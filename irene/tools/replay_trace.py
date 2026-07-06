#!/usr/bin/env python3
"""
replay_trace — replay a saved ARCH-19 trace through the real pipeline and diff (D-6..D-13).

Loads a self-contained trace JSON, seeds a fresh conversation context from the captured
`seed_context`, re-injects the captured audio/text at the level's entry point, and diffs the
fresh result against the recorded one. Two modes (D-10): `--local` (default — run through the
replayer's own config/pipeline; the VAD-tuning case) and `--reproduce` (apply the trace's
captured config subset; fail clearly on a model the replayer lacks, D-16). Extras: `--listen`
(play the captured audio, D-11), `--step` (pause at each pipeline stage, D-12), `--record-out`
(save a second trace of the replay run for side-by-side comparison, D-13).

Replay is NOT bit-exact (LLM is non-deterministic, time/state move on) — it reproduces the input
+ starting state, then diffs. It's a regression/tuning aid (D-6).

Entry point: `irene-replay-trace` (see pyproject [project.scripts]).
"""

import argparse
import asyncio
import base64
import json
import logging
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..components.audio_component import AudioComponent
from ..core.engine import AsyncVACore
from ..intents.models import AudioData

logger = logging.getLogger("irene.replay_trace")


# --------------------------------------------------------------------------------------------
# Pure helpers (unit-tested without standing up a core)
# --------------------------------------------------------------------------------------------

# Action metadata embeds wall-clock fields (e.g. a fire-and-forget action's `started_at`) that move
# on every run; they must be normalized out before diffing, or no command-handler trace could ever be
# a green regression golden. Compare structure/identity, not timestamps.
_VOLATILE_KEYS = frozenset({"started_at", "created_at", "ended_at", "saved_at", "timestamp", "t_ms"})


def _strip_volatile(obj: Any) -> Any:
    """Recursively drop volatile timestamp keys so the diff compares stable structure only."""
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


def write_trace_audio_to_wav(trace: Dict[str, Any], out_path: Path) -> Dict[str, Any]:
    """Extract a trace's captured input audio into a WAV fixture (D-9 / TEST-14).

    The same golden trace then serves BOTH tiers — offline replay *and* the live WS suite
    (record once, test twice). Decodes Irene's trace audio (base64 PCM16) into a standard WAV at the
    captured rate/channels. Raises ``ValueError`` if the trace carries no audio (e.g. a text trace) or
    an unexpected sample format.
    """
    inp = (trace.get("replay") or {}).get("input") or {}
    if inp.get("kind") != "audio" or not inp.get("audio_base64"):
        raise ValueError("trace has no captured audio (not an audio trace) — nothing to extract")
    fmt = inp.get("format") or {}
    afmt = str(fmt.get("format") or "pcm16").lower()
    if afmt not in ("pcm16", "pcm_s16le", "s16le", "pcm"):
        raise ValueError(f"unsupported trace audio sample format {afmt!r} (expected pcm16)")
    pcm = base64.b64decode(inp["audio_base64"])
    rate = int(fmt.get("rate") or 16000)
    channels = int(fmt.get("channels") or 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)  # PCM16
        w.setframerate(rate)
        w.writeframes(pcm)
    return {"path": str(out_path), "rate": rate, "channels": channels,
            "frames": len(pcm) // (2 * max(channels, 1)), "bytes": len(pcm)}


def diff_output(result: Any, recorded: Dict[str, Any]) -> Dict[str, Any]:
    """Diff a fresh IntentResult against the recorded_output oracle (text/success/actions)."""
    fresh = {
        "text": getattr(result, "text", None),
        "success": bool(getattr(result, "success", False)),
        "actions": getattr(result, "action_metadata", None) or [],
    }
    rec = {
        "text": (recorded or {}).get("text"),
        "success": bool((recorded or {}).get("success", False)),
        "actions": (recorded or {}).get("actions") or [],
    }
    fields = {
        "text": {"recorded": rec["text"], "replayed": fresh["text"],
                 "match": (rec["text"] or "").strip() == (fresh["text"] or "").strip()},
        "success": {"recorded": rec["success"], "replayed": fresh["success"],
                    "match": rec["success"] == fresh["success"]},
        "actions": {"recorded": rec["actions"], "replayed": fresh["actions"],
                    "match": _strip_volatile(rec["actions"]) == _strip_volatile(fresh["actions"])},
    }
    return {"match": all(f["match"] for f in fields.values()), "fields": fields}


def apply_config_subset(config: Any, subset: Dict[str, Any]) -> List[str]:
    """Overlay the trace's captured config subset onto a live config (for --reproduce). Returns notes."""
    notes: List[str] = []
    for section, values in (subset or {}).items():
        target = getattr(config, section, None)
        if target is None or not isinstance(values, dict):
            notes.append(f"skip {section} (no such section)")
            continue
        for key, val in values.items():
            if hasattr(target, key):
                setattr(target, key, val)
                notes.append(f"{section}.{key} = {val!r}")
            else:
                notes.append(f"skip {section}.{key} (no such field)")
    return notes


def model_mismatches(provider_models: Dict[str, Any], config: Any) -> List[Tuple[str, str]]:
    """Components whose trace-named provider is NOT among the replayer's configured providers.

    Best-effort under the superset assumption (D-10): we compare the trace's provider ids against
    each component's `providers` block in the replayer config. A returned entry means "the replayer
    can't honour this" — under --reproduce that's a clear failure (D-16).
    """
    out: List[Tuple[str, str]] = []
    for component, model in (provider_models or {}).items():
        section = getattr(config, component, None)
        providers = getattr(section, "providers", None) if section is not None else None
        if providers is None:
            continue  # can't introspect → assume present (superset)
        names = set(providers.keys()) if hasattr(providers, "keys") else set()
        if model and names and model not in names:
            out.append((component, str(model)))
    return out


def seed_context_fields(ctx: Any, seed: Dict[str, Any]) -> None:
    """Populate a fresh UnifiedConversationContext from a saved seed_context dict (D-6)."""
    for field in ("client_id", "room_name", "language", "conversation_history",
                  "handler_contexts", "state_context", "user_id", "supported_languages"):
        if field in (seed or {}) and seed[field] is not None:
            setattr(ctx, field, seed[field])


# --------------------------------------------------------------------------------------------
# Replayer
# --------------------------------------------------------------------------------------------

class TraceReplayer:
    def __init__(self, trace_path: Path, config_path: Path, *, mode: str = "local",
                 record_out: Optional[Path] = None, listen: bool = False, step: bool = False):
        self.trace_path = Path(trace_path)
        self.config_path = Path(config_path)
        self.mode = mode
        self.record_out = Path(record_out) if record_out else None
        self.do_listen = listen
        self.do_step = step
        self.trace: Dict[str, Any] = {}
        self.replay: Dict[str, Any] = {}
        self.recorded: Dict[str, Any] = {}
        self.core: Optional[AsyncVACore] = None  # set by build()

    def load(self) -> None:
        self.trace = json.loads(self.trace_path.read_text(encoding="utf-8"))
        self.replay = self.trace.get("replay") or {}
        self.recorded = self.trace.get("recorded_output") or {}
        if not self.replay.get("input"):
            raise ValueError(f"{self.trace_path} has no replay.input — not a replayable trace")

    async def build(self):
        from ..config.manager import ConfigManager
        from ..runners.composition import build_core

        config = await ConfigManager().load_config(self.config_path)
        if self.mode == "reproduce":
            notes = apply_config_subset(config, self.replay.get("config_subset") or {})
            for n in notes:
                logger.info(f"reproduce: {n}")
            misses = model_mismatches(self.replay.get("provider_models") or {}, config)
            if misses:
                detail = ", ".join(f"{c} → {m}" for c, m in misses)
                raise SystemExit(
                    f"--reproduce cannot honour model(s) the replayer lacks: {detail}\n"
                    f"Install them, or use --local to run the audio through your own pipeline.")
        # --record-out reuses the save-every-request machinery: enable tracing into the chosen dir.
        if self.record_out:
            config.trace.enabled = True
            config.trace.traces_dir = str(self.record_out)
        else:
            config.trace.enabled = False  # a plain replay must not persist anything
        self.core = build_core(config)
        await self.core.start()
        return config

    # -- the run -----------------------------------------------------------------------------

    async def run(self) -> Dict[str, Any]:
        from ..core.trace_context import set_step_hook
        if self.do_step:
            set_step_hook(self._interactive_step)
        try:
            session_id = await self._seed()
            if self.do_listen:
                await self._listen()
            result = await self._reinject(session_id)
        finally:
            if self.do_step:
                set_step_hook(None)
        report = diff_output(result, self.recorded) if result is not None else {"match": False, "fields": {}}
        return report

    async def _seed(self) -> str:
        assert self.core is not None  # build() ran first
        seed = self.replay.get("seed_context") or {}
        session_id = seed.get("session_id") or "replay_session"
        ctx = await self.core.context_manager.get_or_create_context(session_id)
        seed_context_fields(ctx, seed)
        return session_id

    def _step_trace(self):
        """A trace carrying the --step hook for the utterance/text path (workflow mints its own
        for streaming, picking the hook up from the global set in run())."""
        if not self.do_step:
            return None
        from ..core.trace_context import TraceContext
        t = TraceContext(enabled=True)
        t.step_hook = self._interactive_step
        return t

    async def _reinject(self, session_id: str):
        from ..inputs.trace_input import TraceInput

        assert self.core is not None  # build() ran first
        wm = self.core.workflow_manager
        inp = self.replay["input"]
        if inp.get("kind") == "text":
            return await wm.process_text_input(inp.get("text", ""), session_id=session_id,
                                               trace_context=self._step_trace())

        audio_bytes = base64.b64decode(inp.get("audio_base64") or "")
        fmt = inp.get("format") or {}
        rate = fmt.get("rate") or 16000
        channels = fmt.get("channels") or 1
        afmt = fmt.get("format") or "pcm16"
        level = inp.get("capture_level", "utterance")

        if level == "utterance":
            audio = AudioData(data=audio_bytes, timestamp=0.0, sample_rate=rate,
                              channels=channels, format=afmt)
            return await wm.process_audio_input(audio, session_id=session_id,
                                                client_context={"skip_asr": False},
                                                trace_context=self._step_trace())

        # segmenter / raw → re-enter the STREAMING pipeline (VAD → wake → ASR) via TraceInput
        ti = TraceInput(audio_bytes, sample_rate=rate, channels=channels, format=afmt)
        await ti.start_listening()
        last = None
        async for r in wm.process_audio_stream(ti.listen(), session_id=session_id,
                                               skip_wake_word=True):
            last = r
        return last

    async def _listen(self) -> None:
        """Play the captured input audio on the system output (D-11) — best-effort."""
        inp = self.replay["input"]
        if inp.get("kind") != "audio":
            return
        try:
            assert self.core is not None  # build() ran first
            audio = self.core.component_manager.get_component("audio")
            if not isinstance(audio, AudioComponent):
                logger.warning("listen: no AudioComponent available; skipping playback")
                return
            data = base64.b64decode(inp.get("audio_base64") or "")
            fmt = inp.get("format") or {}
            # AudioComponent.play_stream takes raw PCM bytes (it buffers→streams internally).
            await audio.play_stream(data, sample_rate=fmt.get("rate") or 16000,
                                    channels=fmt.get("channels") or 1, sample_width=2)
        except Exception as e:
            logger.warning(f"listen: playback failed ({e}); continuing")

    async def _interactive_step(self, stage: str, data: Dict[str, Any]) -> None:
        """Pause at a pipeline stage: print it, wait for the user (D-12). 'c' runs to the end."""
        if getattr(self, "_step_disabled", False):
            return
        print(f"\n── stage: {stage} ──")
        for k, v in (data or {}).items():
            s = str(v)
            print(f"   {k}: {s[:200]}")
        try:
            ans = await asyncio.get_event_loop().run_in_executor(
                None, input, "[enter] next · 'c' run to end · 'q' quit > ")
        except (EOFError, KeyboardInterrupt):
            ans = "c"
        ans = (ans or "").strip().lower()
        if ans == "q":
            raise SystemExit("replay aborted at --step")
        if ans == "c":
            self._step_disabled = True

    async def close(self) -> None:
        if self.core is not None:
            try:
                await self.core.stop()
            except Exception:
                pass


def _print_report(report: Dict[str, Any], replayer: "TraceReplayer") -> None:
    print("\n========== replay diff ==========")
    print(f"trace : {replayer.trace_path}")
    print(f"mode  : --{replayer.mode}")
    verdict = "MATCH ✓" if report.get("match") else "MISMATCH ✗"
    print(f"result: {verdict}")
    for name, f in (report.get("fields") or {}).items():
        flag = "✓" if f["match"] else "✗"
        print(f"  [{flag}] {name}")
        if not f["match"]:
            print(f"        recorded: {str(f['recorded'])[:160]}")
            print(f"        replayed: {str(f['replayed'])[:160]}")
    if replayer.record_out:
        print(f"\nreplay trace saved under: {replayer.record_out}")
    print("=================================\n")


async def main_async(args: argparse.Namespace) -> int:
    replayer = TraceReplayer(args.trace, args.config, mode=("reproduce" if args.reproduce else "local"),
                             record_out=args.record_out, listen=args.listen, step=args.step)
    replayer.load()
    try:
        await replayer.build()
        report = await replayer.run()
    finally:
        await replayer.close()
    _print_report(report, replayer)
    return 0 if report.get("match") else 2


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a saved trace through the real pipeline and diff against the recorded output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  irene-replay-trace -t traces/<id>.json                 # --local diff (default)\n"
            "  irene-replay-trace -t <id>.json --reproduce            # apply the trace's config\n"
            "  irene-replay-trace -t <id>.json --listen --step        # hear it, pause per stage\n"
            "  irene-replay-trace -t <id>.json --record-out out/      # save a second trace\n"
            "  irene-replay-trace -t <id>.json --extract-wav f.wav    # derive the WS fixture (D-9)\n"))
    parser.add_argument("--trace", "-t", type=Path, required=True, help="Path to the trace JSON file")
    parser.add_argument("--config", "-c", type=Path, default=Path("configs/config-master.toml"),
                        help="Replayer config (default: configs/config-master.toml)")
    parser.add_argument("--reproduce", action="store_true",
                        help="Apply the trace's captured config subset; fail clearly on a missing model "
                             "(default is --local: run through the replayer's own config)")
    parser.add_argument("--listen", action="store_true", help="Play the captured input audio (D-11)")
    parser.add_argument("--step", action="store_true", help="Pause at each pipeline stage (D-12)")
    parser.add_argument("--record-out", type=Path, default=None,
                        help="Directory to save a second trace of the replay run (D-13)")
    parser.add_argument("--extract-wav", type=Path, default=None,
                        help="Extract the trace's captured audio to a WAV fixture and exit (D-9); no replay")
    parser.add_argument("--show-controller", action="store_true",
                        help="Print the nested controller_trace of a satellite trace (ARCH-38) and exit; no replay")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")

    # --show-controller is a pure display transform (ARCH-38): a satellite's merged trace nests
    # the controller's execution envelope — print its story and exit.
    if args.show_controller:
        try:
            trace = json.loads(args.trace.read_text(encoding="utf-8"))
            ctrl = trace.get("controller_trace")
            if ctrl is None:
                print("no controller_trace section — not a satellite trace, or traced without wants_trace")
                sys.exit(1)
            if ctrl.get("declined"):
                print("controller declined the trace request ([trace] allow_remote_request off there)")
                sys.exit(0)
            if ctrl.get("missing"):
                print(f"controller trace missing: {ctrl['missing']}")
                sys.exit(0)
            print(f"controller trace: request {ctrl.get('request_id')}")
            for stage in (ctrl.get("execution") or {}).get("pipeline_stages", []):
                name = stage.get("stage") or stage.get("stage_name") or "?"
                print(f"  {name:<32} {stage.get('processing_time_ms', 0):>8.1f} ms")
            out = ctrl.get("recorded_output") or {}
            if out:
                print(f"  → success={out.get('success')} text='{str(out.get('text', ''))[:120]}'")
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as e:
            logger.error(f"show-controller failed: {e}")
            sys.exit(1)

    # --extract-wav is a pure trace→WAV transform (D-9): no core, no replay, no event loop.
    if args.extract_wav is not None:
        try:
            trace = json.loads(args.trace.read_text(encoding="utf-8"))
            info = write_trace_audio_to_wav(trace, args.extract_wav)
            print(f"wrote {info['path']}  ({info['rate']} Hz, {info['channels']} ch, "
                  f"{info['frames']} frames)")
            sys.exit(0)
        except Exception as e:
            logger.error(f"extract-wav failed: {e}")
            sys.exit(1)

    try:
        sys.exit(asyncio.run(main_async(args)))
    except KeyboardInterrupt:
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"replay failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

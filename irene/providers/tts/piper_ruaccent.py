"""Piper TTS with RUAccent stress preprocessing (ARCH-24 T2, PR3).

`PiperTTSProvider` voiced via espeak-ng phonemization, which is weaker on Russian lexical stress and
homographs than a dedicated accentor. This subclass overrides **only** `_prepare_text` to run
**RUAccent** (Den4ikAI/ruaccent — onnxruntime + numpy, torch-free) first, marking stress (`+`) and
restoring `ё`, then hands the marked text to the inherited sherpa-onnx synth path. Everything else
(model packs, session build, `synthesize_to_file`/`_to_stream`, capabilities) is reused from the base.

**64-bit only (x86_64 / aarch64).** RUAccent depends on the standalone `onnxruntime` wheel, which has
no armv7 build — so the `tts-ruaccent` extra is marked `platform_machine != 'armv7l'` and resolves to
nothing on the WB7, where the plain `piper` provider is the TTS instead.

> Quality note: the RUAccent `+`-mark ↔ espeak-ng stress-input bridge is the open on-device tuning
> item (no aarch64/x86 hardware on hand to A/B Russian quality yet — see the design doc's open checks).
"""

import asyncio
import logging
from typing import Any, Dict, List

from .piper import PiperTTSProvider

logger = logging.getLogger(__name__)


class PiperRuAccentTTSProvider(PiperTTSProvider):
    """`piper` + a RUAccent Russian stress/homograph pass (64-bit only)."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # RUAccent omograph (homograph) model size: 'turbo' (default, fast) | 'tiny' | 'big'.
        self.omograph_model_size: str = config.get("omograph_model_size", "turbo")
        self.use_dictionary: bool = config.get("use_dictionary", True)
        self._accentizer: Any = None  # ruaccent.RUAccent, lazily loaded

    def get_provider_name(self) -> str:
        return "piper_ruaccent"

    async def is_available(self) -> bool:
        # Needs both the sherpa runtime (base) and ruaccent (64-bit only — absent on armv7).
        if not await super().is_available():
            return False
        try:
            import ruaccent  # noqa: F401
        except ImportError:
            logger.warning("ruaccent not installed (64-bit `tts-ruaccent` extra) — piper_ruaccent unavailable")
            return False
        return True

    async def _ensure_accentizer(self) -> None:
        if self._accentizer is not None:
            return

        # RUAccent.load() downloads its models (homograph NN + accent NN + dictionary) from HF on first
        # call. By DEFAULT it writes them into its own *package* dir (site-packages/ruaccent) — ephemeral
        # in a container (re-downloaded on every recreation; the layer may be read-only). Point `workdir`
        # at the mounted models volume so they persist like every other model. (RUAccent still writes its
        # small `koziev` dictionary into the package dir — an upstream limitation; minor, re-fetched cheaply.)
        workdir = self.asset_manager.config.models_root / "ruaccent"

        def build():
            from ruaccent import RUAccent
            workdir.mkdir(parents=True, exist_ok=True)
            acc = RUAccent()
            acc.load(omograph_model_size=self.omograph_model_size, use_dictionary=self.use_dictionary,
                     workdir=str(workdir))
            return acc

        self._accentizer = await asyncio.to_thread(build)
        logger.info(f"Loaded RUAccent (omograph={self.omograph_model_size}, dict={self.use_dictionary}, workdir={workdir})")

    async def _prepare_text(self, text: str) -> str:
        """Override the base no-op: mark Russian stress + restore ё before synthesis."""
        await self._ensure_accentizer()
        return await asyncio.to_thread(self._accentizer.process_all, text)

    def get_capabilities(self) -> Dict[str, Any]:
        caps = super().get_capabilities()
        caps["features"] = list(caps.get("features", [])) + ["ru_stress_accentor"]
        caps["quality"] = "medium-high"  # better Russian stress than plain espeak-ng
        return caps

    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        # Both extras: the sherpa runtime (inherited need) + the 64-bit-only ruaccent stack.
        return ["asr-onnx", "tts-ruaccent"]

    @classmethod
    def get_platform_support(cls) -> List[str]:
        # OS support is the full set; the armv7 exclusion is expressed via get_supported_architectures()
        # (the arch dimension), enforced by the ARCH-24 T3 build gate + the `tts-ruaccent` extra's marker.
        return ["linux.ubuntu", "linux.alpine", "macos", "windows"]

    @classmethod
    def get_supported_architectures(cls) -> List[str]:
        # 64-bit only — ruaccent → standalone onnxruntime, which has no armv7 wheel. On the WB7 use the
        # plain `piper` provider (espeak-ng stress) instead (ARCH-24 T3).
        return ["x86_64", "aarch64"]

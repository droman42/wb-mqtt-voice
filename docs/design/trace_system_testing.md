# Design — trace-driven system testing

**Status:** DESIGN AGREED · 2026-06-27 (D-1..D-14 resolved; implementation pending — TEST-12/13/14) · **Lands in:**
`eval/` (YAML + Makefile) + one small SUT enabler; **reuses** the
existing `eval-commons` `cli_provider` (no new shared code for the core surface). **Builds on:** ARCH-19 trace
record/replay (shipped), the `eval/` harness (`cli`/`ws`/`ux` surfaces), the voice-fixture recorder (TEST-9), and
versioned fixtures (TEST-10).

## 0. Why

Two unmet needs, both served by the trace feature that already exists:

1. **An offline, deterministic, CI-able regression surface.** The WS suite needs a live SUT + a microphone-recorded
   fixture + (for UX) a paid judge, and it exercises a nondeterministic real-time path. Trace **replay** is the
   opposite: fully offline (`irene-replay-trace` builds the pipeline in-process — no server, no mic), with a
   machine-readable verdict (exit `0` match / `2` mismatch) and a diff on `{text, success, actions}`. A recorded trace
   is a **self-contained, portable artifact** carrying the input audio + seed context + an output **oracle** to diff
   against. That is purpose-built for regression.
2. **Failure debugging.** Tracing was originally a *debugging* feature. A failed test should therefore ship a
   **replayable** trace: the developer can `--listen` (hear what the mic heard) and `--step` (pause at each pipeline
   stage) to see exactly where it went wrong, instead of "it failed somewhere."

This design wires both in, without rebuilding anything: the trace machinery and the eval harness already exist; this
is glue + curation + one small enabler.

## 1. The constraint that shapes everything: determinism tiers

Replay is a **regression/tuning aid, not bit-exact reproduction** (per `trace_persistence.md`). ASR is ~deterministic
for the same audio; cheap NLU and rule-handlers (timer, smart-home commands) are deterministic; **LLM replies are not**
(temperature > 0). The eval harness already encodes this exact split (`kind: system` deterministic vs `kind: ux`
judged), so trace cases inherit it.

## 2. Decisions

- **D-1 — Offline golden-trace replay is a new eval surface, driven by the existing `cli_provider`.** A golden-trace
  case is a CLI-contract case pointing at the replay tool — **zero new `eval-commons` code**:
  ```yaml
  - description: regression — «поставь таймер на десять минут» still sets the timer
    metadata: { kind: trace-system }
    vars: { cmd: "irene-replay-trace -t traces/timer_10min.json --local" }
    assert: [{ type: javascript, value: "JSON.parse(output).exit_code === 0" }]
  ```
- **D-2 — Tier the assertions** (mirrors `system`/`ux`):
  | Tier | Covers | Assertion | CI |
  |---|---|---|---|
  | `trace-system` | ASR + cheap NLU + deterministic handlers | `exit_code === 0` (matched the oracle) | ✅ |
  | `trace-ux` | LLM-driven replies | replay `--record-out`, extract the reply, **DeepSeek judge** (reuse `ru-ux`) — *not* exit-code | needs key |
  LLM nondeterminism never makes the suite flaky — those traces route to the judge.
- **D-3 — Golden traces are committed JSON under `eval/traces/*.json`.** They're reviewable text: a behavior change
  shows up as a **diff in the recorded oracle** in the PR — a better regression signal than the live suite gives. A
  separate **`trace.promptfooconfig.yaml`** keeps these apart from `cli.promptfooconfig.yaml` so `make cli` stays
  prerequisite-free (replay needs the models present).
- **D-4 — Axes.** **TARGET does not apply** (replay is in-process; there is no transport/endpoint). **CONFIG applies**
  (`--local` runs under the chosen config) → `make replay CONFIG=voice`.
- **D-5 — Failure-trace capture (live WS) = always-trace + keep-on-failure.** Launch the SUT with `--trace`
  (`make ws TRACE=1`); it writes one trace per request. After the run, a harness post-step keeps **only the failing
  cases'** traces under `eval/traces/failures/` and prunes the rest. This captures the **actual failing run** — unlike
  re-running (D-8), which can't reproduce flaky/nondeterministic failures.
- **D-6 — Correlation enabler (small SUT change).** When tracing is on, the `/ws/audio` response `metadata` carries the
  trace `request_id`. The provider already receives the response metadata, so the harness maps each case → its trace
  **exactly**, instead of fragile time-based matching. Additive, gated on tracing; `config-ui` N/A (it doesn't consume
  `/ws/audio`).
- **D-7 — Failure-trace capture (offline replay) = `--record-out` on mismatch.** Replay with `--record-out <tmp>`; on
  exit-`2`, keep the replayed trace beside the golden. The replay **already diffs** `{text, success, actions}` and
  names the diverging field — "what changed" comes for free, no re-run.
- **D-8 — Re-run-in-trace-mode is a FALLBACK only.** Re-running failed cases against a `--trace` SUT is documented for
  *deterministic* failures when always-on tracing is unwanted; it is **not** the default, because a flaky failure won't
  recur on the re-run and you'd capture a passing trace.
- **D-9 — Trace↔WAV unification (phase 2).** A golden trace carries its audio (base64), so a small extractor derives
  the WS WAV fixture from a trace → **record once, test twice** (offline replay *and* the live WS suite). The trace is
  the canonical input; the WAV is derived. Implemented as a flag on the replay tool / a small `irene` tool (it decodes
  Irene's own trace format, so it stays in this repo, not `eval-commons`).
- **D-10 — Both input kinds are versioned test inputs.** WS WAVs committed (TEST-10); golden traces committed (JSON).
- **D-11 — Recording a golden trace is a curated step.** Run a known-good interaction with `--trace`, review, commit
  the JSON. Curate which traces are `trace-system` (deterministic, exit-code) vs `trace-ux` (LLM, judged) — a human
  call, like choosing fixtures. Mis-tiering is the main risk (§4).

## 3. What this is **not**

- Not bit-exact reproduction (LLM). Not a replacement for the live WS suite — that still tests the real transport and
  the real-time streaming path; this tests pipeline *behavior* offline. Not release-gating initially (enhancement).

## 4. Risks & gotchas

1. **Replay needs the models present** — offline ≠ dependency-free; `make replay` is heavier than `make cli` (which
   brags zero prerequisites). Keep them separate suites so that promise holds.
2. **Determinism tiering must be curated.** A deterministic trace mis-tagged `trace-ux` hides regressions; an LLM trace
   mis-tagged `trace-system` flakes. Document the rule; default new traces to `trace-system` only when the path has no
   LLM.
3. **The oracle drifts intentionally** on behavior changes → the workflow is *re-record + review the JSON diff*, not
   "the test is broken." Document this so a red `trace-system` case is read correctly.
4. **Base64-in-JSON diffs poorly** — the audio is one big blob line; the *oracle* fields review cleanly, which is what
   matters. Acceptable.

## 5. Implementation slices (filed as follow-up tasks)

Per `design-then-implement`, these are filed in the ledger on completion of this design:

- **S1 — Offline golden-trace replay surface** (TEST-12): `eval/traces/` + `trace.promptfooconfig.yaml` +
  `make replay` / `make replay-judge`; record & commit a first deterministic golden trace (timer); add the
  "golden-trace regression" surface to `docs/guides/howto-new-test.md`. Pure YAML + Makefile + the curated trace.
- **S2 — Failure-trace capture for the live WS suite** (TEST-13): `make ws TRACE=1`; the **SUT enabler** (echo
  `request_id` in `/ws/audio` metadata when tracing, D-6); the harness keep-on-failure post-step (a generic
  `eval-commons` helper, D-13); plus `--record-out`-on-mismatch for the offline tier (D-7).
- **S3 — Trace↔WAV unification** (TEST-14, deferred / phase 2): a `--extract-wav` path so one golden trace yields the
  WS fixture (D-9).

## 6. How a user will use it (target state)

```bash
cd eval
make replay CONFIG=voice                 # offline deterministic regression over committed golden traces
make replay-judge                        # the trace-ux tier (DeepSeek)
make ws TARGET=local TRACE=1             # live WS suite; failing cases leave a trace in traces/failures/
irene-replay-trace -t traces/failures/<case>.json --listen --step   # debug a failure: hear it, step it
```

## 7. Decisions on the open questions (resolved 2026-06-27)

- **D-12 — Release-gating: not yet, but on a defined trigger (not "never").** `trace-system` stays `[deferred]` until
  **both**: (a) a curated deterministic golden set covers the release-critical paths (timer + the smart-home command
  path), and (b) it has run **green in CI across two consecutive runs** (proving it's stable/deterministic in the CI
  environment, not just on a dev box). Gating before that would make the release gate flaky; but `trace-system` is the
  cheapest deterministic regression signal available, so it *should* gate once proven — hence a trigger, not a
  permanent exclusion. Promotion = retag the relevant cases/task `[release]` and add the suite to the CI gate.
- **D-13 — The keep-on-failure post-step lives in `eval-commons`** — a small, project-agnostic helper invoked from the
  thin Makefile `ws` target, **not** a per-project bash step. It's reusable (wb-mqtt-bridge will want failure-trace
  capture too) and it honors the harness rule (execution/glue logic lives in `eval-commons`; projects carry YAML + a
  thin Makefile). Its contract is fully generic: read promptfoo's results JSON → for each failing test read
  `metadata.request_id` (D-6) → copy `<traces_dir>/<request_id>.json` into `failures/`. No Irene-specifics, so the
  bridge reuses it unchanged.
- **D-14 — Curation: seed small now, then grow from real failures.** Commit a tiny deterministic seed (timer + one
  smart-home command) for immediate regression value; thereafter the **failure-trace capture loop (D-5) is the growth
  mechanism** — a triaged-and-fixed live failure's trace is promoted to a committed golden regression. This avoids
  speculative over-curation and creates a virtuous loop: failure-tracing (TEST-13) feeds the golden set (TEST-12),
  which in turn is what D-12's promotion trigger measures.

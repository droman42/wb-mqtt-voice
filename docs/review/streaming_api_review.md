# Streaming-API exposure review (QUAL-17)

**Scope:** the WebSocket/streaming-API documentation surface — the hand-rolled AsyncAPI generator and the
`/asyncapi` renderer. **Deliverable:** a keep / upgrade / replace recommendation (acted on in QUAL-18).
**Date:** 2026-06-03.

> **Recommendation in one line:** **Hybrid — REPLACE the renderer, KEEP-and-improve the generator.**
> Drop the 923-line bespoke renderer for the official, maintained `@asyncapi/web-component` (vendored, not
> CDN — offline-first); keep the custom generator (no maintained drop-in fits *raw FastAPI WebSocket →
> AsyncAPI*) but fix its lossy schema conversion and decide 2.6.0-vs-3.0 deliberately.

---

## 1. What exists today (two separate bespoke subsystems)

The streaming-API surface is **two** independently hand-rolled pieces, not one:

| Piece | Location | Size | What it is |
|---|---|---|---|
| **Spec generator** | `irene/api/asyncapi.py` | 474 LOC | `@websocket_api` decorator, `WebSocketRegistry`, custom Pydantic→AsyncAPI **2.6.0** conversion (`pydantic_to_asyncapi_schema`, `_clean_property_for_asyncapi`), a docstring parser (`parse_endpoint_docstring`), and a spec merger. Wired in `irene/runners/webapi_router.py` (`_generate_asyncapi_spec`; routes `/asyncapi.json`, `/asyncapi.yaml`, `/debug/asyncapi`). |
| **Renderer** | `assets/web/templates/asyncapi.html` (81) + `static/js/asyncapi.js` (450) + `static/css/asyncapi.css` (392) | **923 LOC** | A **fully bespoke** DOM renderer served at `/asyncapi`. `asyncapi.js` `fetch('/asyncapi.json')`s and hand-renders channels / operations / schemas / servers into custom HTML with its own nav, collapse/expand, and download links. |

### Documented channels (verified)
Four endpoints carry `@websocket_api` and therefore appear in the spec:

- `/asr/stream` — `AudioChunkMessage` → `TranscriptionResultMessage` (+ `TranscriptionErrorMessage`)
- `/asr/binary` — `BinaryWebSocketProtocol` → `TranscriptionResultMessage` (ESP32 binary)
- `/tts/stream` — `TTSStreamRequest` → `TTSAudioChunk`
- `/tts/binary` — `BinaryTTSProtocol` → `TTSAudioChunk` (ESP32 binary)

### Ledger description corrections (record these)
The QUAL-17 ledger line is inaccurate in three places — corrected here:
1. **The renderer is NOT `@asyncapi/web-component@2.6.4`.** That package name appears only in a *code comment*
   (`asyncapi.py:7`) justifying the **spec version** choice (2.6.0). The renderer at `/asyncapi` is hand-written.
   The code effectively *claims* to use the official component but doesn't.
2. **`/ws` is NOT documented.** The main `/ws` endpoint is not `@websocket_api`-decorated, so it is absent from
   the AsyncAPI spec entirely.
3. **The TTS streaming endpoints ARE documented** (`/tts/stream`, `/tts/binary`) — the ledger omits them.

---

## 2. Assessment of the current implementation

**Strengths**
- Code-first / single-source-of-truth: schemas derive from the live Pydantic message models, so the spec can't
  drift from the wire types.
- Zero runtime third-party dependency; fully offline (matters for an offline-first assistant).
- It works: valid AsyncAPI 2.6.0 JSON/YAML is produced and a usable doc page renders.

**Weaknesses**
- **Lossy schema conversion.** `_clean_property_for_asyncapi` collapses Pydantic `anyOf` (nullable/union) to the
  *first* non-null branch and falls back to bare `{"type": "string"}` for anything it doesn't recognise. Union
  richness and several constraints are silently dropped — the rendered schema is less precise than the real model.
- **923 lines of renderer to own forever.** The bespoke renderer reimplements — incompletely — exactly what the
  official AsyncAPI renderer already does (operations, message examples, schema trees, bindings). Any AsyncAPI
  feature added upstream is a manual port here.
- **Fragile docstring parser.** `parse_endpoint_docstring` extracts "protocol flow / features / benefits" from
  free-text docstrings with heuristic header matching into `x-` extensions — a maintenance liability that the
  custom renderer is the only consumer of.
- **Stuck on AsyncAPI 2.6.0.** 3.0 (current major) restructured channels/operations; the generator hard-codes 2.6.0.
- **Binary protocols under-described.** The ESP32 binary frame formats are conveyed via a JSON message schema +
  docstring prose, not via AsyncAPI **message bindings** — the part most valuable to an embedded client is the
  least machine-described.

---

## 3. Modern alternatives evaluated (June 2026)

| Option | Fit | Verdict |
|---|---|---|
| **`@asyncapi/web-component` / `@asyncapi/react-component`** (official renderer) | Framework-agnostic web component / standalone bundle; actively maintained (web-component **2.6.5**, ~5 months old); renders AsyncAPI **2.x and 3.x**. Drop-in: one `<asyncapi-component>` element fed the existing `/asyncapi.json`. | **Adopt for the renderer.** This is literally what the code comment claims to use. Replaces 923 LOC with a maintained dependency. Must be **vendored locally** (offline-first), not loaded from a CDN. |
| **FastStream** (ag2ai) | Code-first AsyncAPI from Pydantic — but it is a **message-broker framework** (Kafka/RabbitMQ/NATS/MQTT/Redis). Using its generator means routing the WS endpoints through FastStream. | **Reject for now.** Wrong shape — these are raw FastAPI WebSocket endpoints, not broker subscriptions. Adopting it = rewriting the transport layer for a docs win. (Revisit only if/when the MQTT work in ARCH-7/8 brings a real broker in — then FastStream's AsyncAPI could come for free.) |
| **`asyncapi-python`** | Generates Python *from* an AsyncAPI 3 spec (spec-first codegen). | **Reject.** Opposite direction (spec→code); we are code→spec. |
| **AsyncAPI Studio (embed)** | Full editor/viewer; heavier, editor-oriented, not meant to be embedded as a read-only docs panel in-app. | **Reject** for the in-app `/asyncapi` page; useful only as an external authoring tool. |

**Finding:** there is **no maintained drop-in** for "introspect FastAPI raw-WebSocket routes → AsyncAPI spec"
today. The generator side genuinely has to stay bespoke (or move to a broker framework, which is a much larger
architectural decision). The **renderer** side, by contrast, has a clean, maintained, offline-vendorable
replacement.

---

## 4. Recommendation (keep / upgrade / replace)

**Hybrid.**

### 4a. Renderer → **REPLACE** (high value, low risk) — the QUAL-18 first move
- Delete `assets/web/static/js/asyncapi.js` + `static/css/asyncapi.css` + the bespoke `asyncapi.html` body.
- Serve the official `@asyncapi/web-component` **standalone bundle, vendored** under `assets/web/static/` (no CDN —
  the assistant must render its own docs offline). The `/asyncapi.json` route is unchanged; the component consumes it.
- Net: **≈ −900 LOC**, a spec-complete + maintained renderer (operations, bindings, examples, schema trees), and
  the code stops misrepresenting what it uses. **Invariant #4** is unaffected (config-ui is separate).

### 4b. Generator → **KEEP, but improve** (no drop-in fits)
- **Keep** `irene/api/asyncapi.py` — code-first introspection of FastAPI WS routes is the right model and has no
  maintained replacement.
- **Fix the lossy conversion**: stop flattening `anyOf`/unions and the string-fallback in
  `_clean_property_for_asyncapi`; prefer passing Pydantic's JSON Schema through with minimal massaging.
- **Decide 2.6.0 vs 3.0 deliberately.** The new renderer supports both, so staying on 2.6.0 short-term is safe;
  moving to 3.0 is a *separate, scoped* change (channels/operations restructure) — recommend deferring to its own
  QUAL-18 sub-step rather than bundling it with the renderer swap.
- **Describe binary frames via message bindings** so ESP32 clients get a machine-readable contract.
- Consider retiring the heuristic docstring parser once the official renderer (which won't read the custom `x-`
  extensions) is in — or keep it only if those extensions are explicitly mapped to renderer-understood fields.

### Why not "keep everything"
It works, but it commits the project to maintaining a 923-line renderer that a maintained dependency already does
better, while the code documents a dependency it doesn't actually use. The renderer swap is the cheapest, highest-
leverage change on this surface.

### Why not "replace everything"
No maintained tool introspects raw FastAPI WebSocket routes into AsyncAPI; the only "replace the generator" path
(FastStream) means adopting a broker framework and rewriting the WS transport — out of proportion to a docs task,
and better revisited alongside the ARCH-7/8 MQTT work if a broker actually lands.

---

## 5. Hand-off to QUAL-18 (act-on)

Ordered, each independently shippable:
1. **Vendor + wire `@asyncapi/web-component`** at `/asyncapi`; delete the bespoke renderer (≈ −900 LOC). *(P-first)*
2. **Fix `_clean_property_for_asyncapi`** lossy union/nullable handling.
3. **(Optional, scoped separately)** emit **AsyncAPI 3.0**; add **binary message bindings** for the ESP32 frames.
4. Retire/repoint the docstring `x-` extension parser once the official renderer is in.

Correctness note for QUAL-18: the `/ws` main socket is currently undocumented — decide whether it *should* be
documented (decorate it) or is intentionally internal.

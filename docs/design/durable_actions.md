# Durable Actions — the fire-and-forget durability substrate (ARCH-27)

**Status:** design AGREED 2026-07-02 (interactive session; all decisions user-confirmed). Implementation → **ARCH-28**.
**Evidence base:** `docs/review/faf_durable_execution_review.md` (QUAL-56) — the F&F subsystem scores zero on every
durable-execution axis by design; `wb-mqtt-bridge` comparative analysis (patterns + pitfalls). Store-correctness
prerequisites already landed as **BUG-19**.
**Scope statement (user):** timers are the only consumer needing durability *today*, but future intent handlers
(smart-home arc — ARCH-8 device actions and beyond) **will require it** — so this is a platform substrate with
binding authoring rules, not a timer patch.

---

## 1. Problem

An F&F action is a promise ("I'll ring in 10 minutes"). The promise lives only in process memory
(`ClientRegistry._actions`, deliberately never persisted): a restart at minute 5 silently breaks it, and
*"list timers"* then denies the promise ever existed. Completions are delivered at-most-once with five
independent silent-drop points, and failures are suppressed by default. Full autopsy: the QUAL-56 review.

## 2. Decisions

### D-1 — Durability is an explicit, per-launch opt-in
`execute_fire_and_forget_with_context` / `execute_fire_and_forget_action` gain a keyword-only **`durable: bool = False`**.
Ephemeral remains the default: TTS/audio (seconds-scale; nothing meaningful to recover) never touch disk.
The timer handler sets `durable=True`. **Rule:** *an action promising effects beyond the current interaction MUST
declare `durable=True`* (binding via D-10). Rejected alternatives: persist-everything (flash churn for useless
records), duration-threshold auto (implicit; short-timeout actions with lasting effects silently escape).

### D-2 — Store: one atomic JSON file behind a port, under the ASSET-MANAGED root
A **`DurableActionStorePort`** (hexagonal, `irene/core/` interfaces) with a default adapter writing
**`<assets_root>/state/durable_actions.json`** via **temp-file + `os.rename`** on every mutation. Zero new
dependencies, human-debuggable, and at voice scale (a handful of concurrent durable records; writes only at
launch/completion/redelivery) single-process asyncio makes races a non-issue. SQLite (the bridge's `aiosqlite`
pattern) remains the drop-in upgrade behind the same port if device actions ever raise the write rate.

**Location is load-bearing (user correction 2026-07-02).** The store lives under the **asset-management tree**
— a new **`state/` folder** exposed as `AssetConfig.state_root` (sibling of `models_root`/`cache_root`/
`traces_root`, created by `_create_directories`, path resolved through the asset config, root controlled by
`IRENE_ASSETS_ROOT`) — because `assets_root` is what gets **volume-mounted outside the Docker container**: a
container redeploy must not wipe the very records that exist to survive restarts. `state/` is deliberately NOT
`cache/`: cache is deletable by definition; durable action records are not. **Corollary fixed in the same
slice:** `client_registry.json`'s default path is cwd-relative `cache/` today (i.e. `/app/cache` **inside** the
container) — client registrations silently don't survive a container replacement either. Its default moves to
`<assets_root>/state/client_registry.json` (read-fallback to the old path for migration).

**Write discipline (the bridge's lessons, both directions):**
- *Persist at launch, delete at completion — in the same operation as the in-memory store mutation.* The bridge's
  stale-`active_scenario` bug (deactivated scenario resurrecting on restart because completion never cleared the
  key) is the canonical failure; deletion is not an afterthought.
- *Ephemeral-field filter:* the persisted record carries **no live-task bookkeeping** (no task refs, no monitor
  keys) — only what re-arm needs (§D-3 schema).
- *Shutdown discipline:* flush any pending write before teardown; exit bookkeeping must never mark in-flight
  records completed/failed (they are exactly what recovery needs).
- *Anti persist-without-restore rot:* **persist + restore + a restart test ship in the same change** (ARCH-28
  definition of done). A store nobody reads back is a lie about durability — the bridge demonstrates this today.

**Persisted record schema (v1):**
`{action_name, domain, handler, physical_id, session_id, room_id, source, started_at, deadline, durable: true,
redeliver: bool, rearm: {method, params}, metadata: {language, completion_message}, schema: 1}`
plus, for §D-6, a parallel `undelivered` list of completion notices awaiting redelivery.

### D-3 — Recovery: re-arm by relaunch through the normal path (reconcile-by-diff, not log replay)
At startup (after components initialize, before inputs accept traffic) a **reconciler** reads the store:
- **deadline in the future** → re-arm: the owning handler's **`rearm(record)` hook** relaunches the action through
  the ordinary launch path with the *remaining* duration (recomputed — the diff analog), same `action_name`
  (stable identity across restart), `durable=True` again. For timers: `_run_timer(remaining, message, …)`.
- **deadline passed** → §D-4 policy.
- **record's handler unknown/undecodable** → announce-as-expired + delete (never wedge startup on a bad record).
The `rearm` hook is part of the handler durability contract (D-10). No command-log journaling — the record *is*
the intent; recovery re-derives the schedule.

### D-4 — Missed deadlines: fire-with-apology inside a grace window
Deadline passed while down: **missed by ≤ `grace_window` (default 1 h)** → the action's completion fires
immediately with a localized *"…expired while I was away"* apology prefix to the owning room; **older** → an
expiry announcement (no ring). Both route through the normal notification path. The kitchen-timer case (deploy or
power blip mid-countdown) degrades to *late*, never to *silent*.

### D-5 — Failure notifications: announce by default
Flip the default notification policy: an F&F **failure speaks a short error to the originating room**
(`critical_only` default → False). The user asked for something and it didn't happen — that is never below
threshold. **Sub-30 s success suppression stays** (the immediate response already confirmed quick actions).
Note (recorded, out of scope here): notification *preferences* remain session-scoped and reset on eviction —
if per-user tuning ever matters, prefs move to the physical-id scope; not in ARCH-28.

### D-6 — Redelivery: handler-declared, at-least-once for those who ask
Launch gains **`redeliver_on_reconnect: bool = False`** (only meaningful with `durable=True`). When a flagged
action completes and the owning room's reply channel is offline, the completion notice is written to the store's
`undelivered` list (TTL = the grace window) and **delivered on the client's next registration** (hook:
`ClientRegistry.register_client` → drain matching notices). Timer sets it — a ring survives a satellite reboot.
Everything unflagged keeps today's best-effort drop-with-history. This makes delivery **at-least-once for flagged
durable actions** (a reconnect racing a live delivery may double-announce — acceptable for an idempotent spoken
notice), best-effort otherwise.

### D-7 — Retry machinery: CUT
`_execute_with_retry` / `_is_transient_failure` / the `max_retries`/`retry_delay` launch params are deleted
(**QUAL-61**, now unblocked). Rationale: dead config (never invoked in production), blind whole-coroutine
re-invocation is unsafe without per-action idempotency (double-fired device commands), and the bridge likewise
surfaces per-step failures rather than blind-retrying. A future handler that needs retries owns them
domain-specifically, backstopped by D-5's failure announcement. Also cut per QUAL-61: `AsyncTimerManager`
(the substrate re-arms via relaunch — it has no role) and the never-read `NotificationMessage` retry fields.

### D-8 — Idempotency & identity
BUG-19's uuid-suffixed names + identity-safe store are the naming contract: every launch mints a unique
`action_name`; restart **re-arm reuses the persisted name** (one identity across the process boundary — history
and contextual commands keep working). No cross-launch dedup of user intents (saying "set a timer" twice = two
timers — correct); idempotency machinery beyond this is deferred until a consumer needs it.

### D-9 — Observability: minimal read-only REST
Two GETs on the existing monitoring router: **`/monitoring/actions`** (live actions across identities: name,
domain, owner physical_id/room, started_at, deadline, durable/redeliver flags) and
**`/monitoring/actions/history?physical_id=`** (the per-identity recent/failed history). Read-only — no
cancel-by-REST (would bypass voice-side confirmation and re-open the API surface QUAL-59 deleted).

### D-10 — The handler-authoring rules and where they bind
Source of truth for the *contract* = **this document (§3)**. User-facing prose lands as a new section in
**`docs/guides/howto-new-intent.md`** (matching its voice; written in ARCH-28 alongside the working substrate).
A short **`durable-actions` invariant is added to `CLAUDE.md`** when ARCH-28 lands, making the contract binding
on every future task, pattern as `cross-repo-source-of-truth`: rule always in context, detail referenced.

## 3. Handler-authoring durability rules (the contract — v1)

1. **Declare your class.** Every F&F launch states its durability: default ephemeral; `durable=True` iff the
   action promises effects beyond the current interaction (rings later, changes device state later, reports
   later). When in doubt, it's durable.
2. **Durable ⇒ re-armable.** A handler launching durable actions MUST implement the `rearm(record)` hook and
   keep its `rearm.params` self-contained (everything needed to relaunch lives in the persisted record — no
   reliance on in-memory context).
3. **Never hand-roll schedules.** No `asyncio.sleep`-based future promises outside the substrate; no ad-hoc
   `create_task` timers. If it waits to act, it goes through the durable launch.
4. **Decide redelivery.** Set `redeliver_on_reconnect=True` iff a missed completion notice loses real value
   (timer ring: yes; "playback started": no).
5. **Fail loudly.** Raise on failure (or `return False` — the choke point converts it); never swallow-and-return-
   True. Failures are announced by default (D-5) — that is the contract, don't route around it.
6. **Names are minted, not chosen.** Use the launch's naming scheme (unique per launch); never reuse or derive
   colliding names (BUG-19).

## 4. Implementation plan (→ ARCH-28)

Slices, each leaving the tree green: **(1)** `AssetConfig.state_root` (`<assets_root>/state/`, added to
`_create_directories`) + `DurableActionStorePort` + atomic-JSON adapter + record schema + unit tests, **and the
`client_registry.json` default relocation** to `state/` with old-path read-fallback (same container-lifetime
flaw, same fix); **(2)** launch/completion wiring (`durable`/`redeliver_on_reconnect` params, persist-at-launch,
delete-at-completion) + timer opts in; **(3)** startup reconciler + `rearm` hook + fire-with-apology/expiry
messages (localized ru/en) + **the restart test** (launch durable timer → new store instance + reconcile →
asserts re-arm and both missed-deadline behaviors); **(4)** redelivery drain on client registration + TTL;
**(5)** D-5 policy flip; **(6)** D-9 monitoring endpoints; **(7)** docs: `howto-new-intent.md` section +
`CLAUDE.md` `durable-actions` invariant + `docs/architecture` touch-ups where behavior is described.
QUAL-61 (cuts) can run any time after slice 2 (it deletes what nothing then references).

## 5. Rejected / deferred

- SQLite store now (deferred behind the port until write rates demand it) · persist-everything ·
  duration-threshold auto-durability · retry-in-substrate · cancel-by-REST · cross-launch intent dedup ·
  physical-id-scoped notification preferences (recorded gap, separate decision) · durable scheduler as a
  standalone component (`AsyncTimerManager` resurrection) — the store + reconciler *is* the scheduler.

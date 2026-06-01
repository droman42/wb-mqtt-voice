# Fire-and-Forget (F&F) Review — QUAL-8 [FAF]

**Status:** complete (2026-06-01). **Backs:** QUAL-9 (remediation), TEST-3, DOC-4 (retire `docs/fire_forget_issues.md`). **Re-validates:** the 6 issues in `docs/fire_forget_issues.md` (Sep 2025).
**Method:** three parallel deep-reads (launch/lifecycle · context state · legacy-issue re-validation + monitoring), then synthesis. The three headline P0s spot-verified directly.

---

## TL;DR — verdict

**Fire-and-forget is broken end-to-end, and the legacy doc that marks it "✅ COMPLETED" is materially false.** The Sep-2025 work added a lot of plumbing — done-callbacks, metrics, notifications, context-manager injection — but the subsystem is dead because of a **domain-vs-action_name key mismatch** that makes every completion lookup miss, compounded by a **call to a method (`get_or_create_context`) that doesn't exist**. On top of that, **timers fail outright on launch** with a duplicate-`session_id` `TypeError`. Net runtime behavior: timers don't start at all; audio/voice actions start but their tracking entries are **never removed** (unbounded `active_actions` leak), completions/failures are **never recorded** to metrics or notifications, and readers see every past action as **perpetually running** — corrupting "what's running?" answers and contextual-command disambiguation.

**Severity tally:** 5 × P0, 8 × P1, 6 × P2.

### Themes
1. **Wired but dead** (same disease as QUAL-12/14): the lifecycle is fully plumbed but non-functional — completion/metrics/notifications all live inside an `if remove_completed_action(...)` block that always returns `False`.
2. **Key confusion is the root cause:** launch keys actions by unique `action_name`; every reader/remover keys by coarse `domain`. They never align.
3. **Concurrency-incorrect even if fixed:** both `active_actions` and metrics `_active_actions` are keyed by `domain` only, so two timers (both `domain="timers"`) clobber each other.
4. **Lifecycle hazards:** action tasks are orphaned (GC-cancellable), timeout monitors flat-sleep for the full 300s, cleanup runs only at shutdown, and the memory manager never prunes `active_actions`.
5. **Scope was overstated:** ~13 call sites in 3 handlers (not "~83"), several of them backgrounding trivially-fast ops (cancel/stop) that gain nothing.

---

## The 6 legacy issues — re-validation

| # | Legacy claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Key mismatch `active_actions` (plural) vs `active_action` (singular) | **CHANGED — still broken** | Plural/singular fixed, but morphed into a **domain vs action_name** mismatch: launch stores `active_actions[action_name]` (`base.py:500`; write-back `voice_assistant.py:690`, `workflow_manager.py:1025`), removal uses `remove_completed_action(domain)` (`base.py:636`, `models.py:337`). `action_name != domain` always (timer: `timer_id` vs `"timers"`). |
| 2 | Completion write-back not integrated with context manager | **CHANGED — unreachable** | Callbacks now exist (`base.py:582→619→636`) but gated by the failing `remove_completed_action`; and they call the **non-existent** `get_or_create_context` (`base.py:633`) → `AttributeError` swallowed (`base.py:703`). |
| 3 | Memory leak — completed actions never removed | **CONFIRMED** | Direct consequence of #1/#2: entries stored under `action_name`, removed by `domain` → never found → `active_actions` grows unbounded; `MemoryManager` never trims it (`memory_manager.py:185-212`). |
| 4 | Inconsistent success/failure metadata shapes | **FIXED** | Startup-failure returns the same `active_actions` shape with `status:"failed"` (`base.py:560-574`), enforced by `_validate_action_metadata` (`base.py:962`). (Moot in practice — entries are never consumed.) |
| 5 | No error propagation / no success-failure metrics | **CHANGED — wired but unreachable** | `record_action_start` fires (`base.py:489`), but `record_action_completion` + both notifications are nested in the failing `if remove_completed_action(...)` block (`base.py:656-693`) → metrics show monotonic started-never-completed; no failure ever reaches the user. |
| 6 | Completion callbacks lack context-manager access | **FIXED mechanically** | Context manager is injected + captured in the callback closure (`base.py:520-521,633`) — but it operates on the wrong key (#1) and calls the missing method (#2). |

**Summary:** 1 FIXED (#4), 1 FIXED-but-moot (#6), 2 CHANGED-still-broken (#1, #5), 1 CONFIRMED (#3), 1 CHANGED-unreachable (#2). The doc's "all issues resolved" is false — the core lifecycle does not work.

---

## Findings

- **[P0]** **Timers crash on launch — duplicate `session_id`.** `execute_fire_and_forget_with_context` passes `session_id=context.session_id` explicitly (`base.py:125`) and forwards `**kwargs` (`base.py:130`); all 3 timer call sites also pass `session_id=context.session_id` in kwargs (`timer.py:228,285,348`) → `TypeError: got multiple values for keyword argument 'session_id'`. Only `ValueError` is caught (`timer.py:245`), so timer creation **fails outright**. (Audio/voice handlers don't pass `session_id`, so they escape it.) The same call also splices `*args` after keyword args (`base.py:129`) — fragile. *(verified)*
- **[P0]** **Domain/action_name key mismatch kills the whole lifecycle.** Launch builds `active_actions[action_name]` (`base.py:500`); both write-back processors store by `action_name` (`voice_assistant.py:690`, `workflow_manager.py:1025`); all removal/timeout/cancel paths key by `domain` (`base.py:636,766,905,1266`; `models.py:337`). `remove_completed_action(domain)` returns `False` → completion body never runs → entries never removed, metrics/notifications never fire. *(verified)*
- **[P0]** **Completion/notification callbacks call a non-existent `get_or_create_context`.** Real `ContextManager` exposes `get_context` (`context.py:61`), not `get_or_create_context`; the latter is called at `base.py:633`, `notifications.py:174,229`, `debug_tools.py:101` → `AttributeError`, swallowed by broad `except` (`base.py:703,778`). Completion write-back is dead even independent of the key bug. *(verified)*
- **[P0]** **Action tasks are orphaned (GC-cancellable).** `execute_fire_and_forget_action` keeps only a local `task` (`base.py:482/486`) + a done-callback; the task is never stored in an instance collection (only `id(task)` in metadata). Per CPython semantics an unreferenced `create_task` result can be GC'd and silently cancelled mid-flight. Only the *timeout monitor* gets a strong ref (`self._timeout_tasks`, `base.py:531`), and only when `timeout>0`.
- **[P0]** **`active_actions` grows unbounded.** Consequence of the key mismatch + no pruning: every F&F action leaves a permanent zombie entry; `MemoryManager.perform_system_cleanup` trims `recent_actions`/`failed_actions`/`conversation_history` but **never `active_actions`** (`memory_manager.py:185-212`). Inflates context memory and every reader.
- **[P1]** **Same-domain actions clobber each other.** `active_actions[domain]` (`models.py:300`) and metrics `_active_actions[domain]` (`metrics.py:196`) hold one entry per domain; two concurrent timers (`domain="timers"`) overwrite one another's tracking and metric. Even after the key fix, the domain-keyed metrics need a per-action key.
- **[P1]** **`recent_actions`/`failed_actions`/`action_error_count` stay empty in practice** (the only populator is the unreachable `remove_completed_action`), so readers — recent-activity gating (`conversation.py:669-683`), failure summaries (`models.py:545-564`) — always see empty/stale state.
- **[P1]** **Readers see perpetually-"running" actions.** Orchestrator contextual-command resolution and confirmation logic count `active_actions` as live (`orchestrator.py:148-177`, `context.py:587-715`); NLU/conversation inject them as context (`nlu_component.py:1051`, `conversation.py:590`). Never-cleared entries corrupt disambiguation and "what's running?".
- **[P1]** **Timeout monitor flat-sleeps the full timeout.** `_monitor_action_timeout` does `await asyncio.sleep(timeout)` (`base.py:748`) instead of awaiting the task; fast actions finish in ms but the monitor lives the full default 300s (its early cancel depends on the broken domain lookup) → zombie monitors pile up.
- **[P1]** **No periodic cleanup** — `cleanup_timeout_tasks` runs only at shutdown (`intent_component.py:101`).
- **[P1]** **Completion handler spawns another orphan task** — `_handle_action_completion` schedules `_update_context_on_completion` via `asyncio.create_task` with no ref/callback (`base.py:608`).
- **[P1]** **Two divergent write-back processors** — `voice_assistant._process_action_metadata` (`:684`) and `workflow_manager._process_action_metadata_integration` (`:993-1068`) re-implement the copy with different context-fetch semantics (`get_or_create_context` vs `get_context`→possibly `None`); the latter drops `add_active_action`'s room/session enrichment. State depends on which path runs.
- **[P2]** Read-after-pop: completion reads `active_actions.get(domain)` *after* popping it (`base.py:651,671`) → zero `retry_count`/`duration` even once the key is fixed. `task_id=id(task)` is unstable after GC. Timer cancellation has an unfinished `TODO: remove cancelled action` (`timer.py:631`) → cancelled timers leak. F&F is used for trivially-fast ops (cancel/stop) that don't need backgrounding. **Plan correction:** ~13 call sites in 3 handlers (timer/audio_playback/voice_synthesis), not "~83". `docs/fire_forget_issues.md` is materially false (claims all 6 resolved).

---

## Monitoring / metrics / notifications

Wiring is real and on-by-default — `MonitoringComponent` builds `MetricsCollector`/`NotificationService`/`ActionDebugger`/`MemoryManager` and injects them into every handler (`monitoring_component.py:173-209`). **But only `record_action_start` ever runs** (`base.py:489`); `record_action_completion` and both notifications are nested in the failing `if remove_completed_action(...)` block (`base.py:656-693`), so metrics show monotonically rising started/concurrent counts that never decrement, and no completion/failure notification ever reaches the user. `_active_actions` is domain-keyed (`metrics.py:196`) → same concurrent-same-domain corruption.

---

## Ranked remediation (feeds QUAL-9)

**P0 — make F&F actually function:**
1. **Fix the timer launch crash** — drop the duplicate `session_id` (give `execute_fire_and_forget_with_context` a real `session_id` param and stop passing it in kwargs; remove the `*args`-after-kwargs splice).
2. **Unify the action key** — key `active_actions` (and metrics `_active_actions`) by the **unique `action_name`** end-to-end; make completion/timeout/cancel remove by the same `action_name` the callback already has. This fixes the leak (#3), the dead completion (#2/#5), *and* the same-domain clobber in one move.
3. **Fix `get_or_create_context`** — add it to `ContextManager` (get-or-create) or call `get_context` everywhere (`base.py:633`, `notifications.py:174,229`, `debug_tools.py:101`).
4. **Hold strong references** to action tasks (instance set; discard in the done-callback) to prevent GC cancellation.
5. **Bound + prune `active_actions`** — cap it and have `MemoryManager` trim it; add periodic cleanup of finished entries (not just shutdown).

**P1:** await the task in the timeout monitor (`wait_for`) instead of flat-sleeping; capture `active_actions[name]` before pop; collapse the two write-back processors into one; per-action metrics keying; finish the timer-cancellation context cleanup (`timer.py:631`).

**P2:** stop backgrounding trivially-fast ops; replace `id(task)` with a stable UUID; retire/replace `docs/fire_forget_issues.md` (DOC-4).

## Cross-references
- **QUAL-9** [FAF] — execute the P0/P1 remediation. **TEST-3** — once it works, add lifecycle coverage (launch→complete→error→timeout→cleanup→context).
- **DOC-4** — retire `docs/fire_forget_issues.md` (materially false); a banner has been added pending QUAL-9.
- **Systemic pattern** — fourth instance of "plumbed-but-dead / configured-name-doesn't-resolve" (with QUAL-10 cascade names, QUAL-12 dead stages, QUAL-14 phantom console). Worth a cross-cutting "wire-up integration test" + startup assertions.

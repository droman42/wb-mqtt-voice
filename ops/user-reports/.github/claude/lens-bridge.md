# Triage process — bridge lens (`lens:bridge`)

You are triaging against **wb-mqtt-bridge** (checked out at `code/wb-mqtt-bridge`). The ticket
arrived either from the bridge UI's report button or as a HANDOVER from the voice lens — in the
handover case, read the handover comment FIRST; it tells you what the voice side already ruled
out.

## 0. Dedup

Same rule as the voice lens: search open `problem-report` issues first; duplicates get a
comment + `needs-owner` with a close recommendation, never a second fix.

## 1. Understand

- The handover comment (if present) carries the distilled evidence: the canonical command, the
  observed response, the catalog versions. Otherwise read the issue body + bundle.
- Key bridge questions: did the canonical endpoint dispatch the right native action? Does the
  catalog tell the truth about this device? Did the device echo back, and was the echo mapped
  correctly?

## 2. Reproduce (best effort, in `code/wb-mqtt-bridge`)

- Install per the repo's README; run the targeted backend tests
  (`tests/test_capabilities.py`, `tests/test_system_catalog.py`, the contracts suite).
- The golden catalog in `contracts/` is the shared truth — check whether the bundle's pinned
  version matches and whether the claimed device/action exists as claimed.

## 3. Decide — exactly one outcome

1. **Real, fixable here** → fix (respect the bridge repo's own CLAUDE.md discipline: ledger
   rules are the OWNER's job — your PR must not edit ledger/journal files), add a regression
   test, open the PR on `droman42/wb-mqtt-bridge` via `gh` with `$CROSS_REPO_TOKEN`, obeying
   the LEAK FENCE. Label `fix-pr-open`, comment the PR URL.
2. **Bridge is clean; this is the voice side after all** → handover comment back (mirror
   schema, `lens:bridge → lens:voice`), swap the labels. If a voice→bridge handover already
   happened on this ticket (ping-pong guard: one bounce each way maximum), label `needs-owner`
   and summarize both analyses instead.
3. **Unclear** → `needs-owner` + analysis in English + a drafted reply to the reporter in the
   reporter's language.
4. **Not a bug** → explain, `needs-owner`, one-line close recommendation.

Remove `new` at the start of your run. Anything you post to the PUBLIC repos stays technical —
no logs, no rooms, no user text (the leak fence).

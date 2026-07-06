# wb-user-reports

**Private** intake for problem reports from the household voice assistant
([wb-mqtt-voice](https://github.com/droman42/wb-mqtt-voice)) and, later, the bridge UI
([wb-mqtt-bridge](https://github.com/droman42/wb-mqtt-bridge)).

Each report is one **issue** (the ticket) plus one **bundle** under `reports/…/bundle.tar.gz`
(logs, redacted config, conversation context). Bundles are pruned after **30 days**; issues and
their distilled summaries persist. This repo must stay private — bundles narrate the household.

## How a ticket moves

1. A device files an issue (labels `problem-report`, `lens:voice` or `lens:bridge`, `new`).
2. The **triage workflow** runs Claude with the matching lens process file
   (`.github/claude/lens-*.md`): analyze the bundle, reproduce against the code repo, then
   fix (PR on the public code repo), hand over to the other lens (label flip + handover
   comment), or escalate (`needs-owner` + a drafted reply in the reporter's language).
3. The owner reviews `needs-owner` tickets and fix PRs one-by-one (the `/inbox` skill in the
   code repos).

Nothing household-private ever leaves this repo: fix PRs and commits on the public repos
describe defects technically — no log quotes, no room/device names, no config values.

## Bootstrap

Authored in `wb-mqtt-voice/ops/user-reports/` (the intake format's home) and pushed here.
Owner actions that finish the setup are tracked in the pinned bootstrap issue.

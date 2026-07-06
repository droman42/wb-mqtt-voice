# Triage process — voice lens (`lens:voice`)

You are triaging a problem report against **wb-mqtt-voice** (checked out at
`code/wb-mqtt-voice`). The reporter is a household user speaking to the voice assistant —
usually in Russian — with no GitHub identity. Design reference:
`code/wb-mqtt-voice/docs/design/problem_reports.md`.

## 0. Before anything: dedup

Search open `problem-report` issues for the same symptom (`gh issue list -l problem-report`).
If this is a duplicate, post a comment linking the original, label this ticket `needs-owner`
with a one-line close recommendation, and STOP. Never fix the same bug twice in parallel.

## 1. Understand

- Read the issue body (free text is verbatim from the user — its language is the language you
  must use for any reply draft).
- Download the linked bundle; read `metadata.json`, `requests.json` (the NLU verdicts around
  the failure), `conversation.json`, `actions.json`, then the logs. The issue body's synopsis
  usually suffices — open the tarball when it doesn't.
- Locate the failing moment: which utterance, which intent, which provider won, what the
  handler answered, what the log shows around that timestamp.

## 2. Reproduce (best effort, in `code/wb-mqtt-voice`)

- `uv sync --all-extras`, then targeted: `uv run pytest irene/tests -q` for the suspect area;
  the in-process NLU probe pattern from `irene/tests/test_qual64_matcher_scoring.py` for
  routing complaints; `uv run irene-cli -c configs/config-example.toml -e "<utterance>"` for
  pipeline behavior (no models/keys needed for the text path).
- The catalog in the bundle's metadata names the pinned version — compare with
  `eval-commons` expectations when a device command misbehaved.

## 3. Decide — exactly one outcome

1. **Real, fixable here** → fix at the right altitude (donation/pattern fixes before handler
   special-cases — see the repo's CLAUDE.md discipline), add/extend a regression test, run the
   affected suites, then open a PR on `droman42/wb-mqtt-voice` using `gh` with
   `$CROSS_REPO_TOKEN`. PR text obeys the LEAK FENCE (technical description only; reference
   this ticket by number, e.g. `wb-user-reports#N` — the link resolves only for the owner).
   Label this ticket `fix-pr-open` and comment the PR URL.
2. **Voice is clean; evidence points at the bridge** (wrong native action for a correct
   canonical command, catalog lies, echo mismatch) → post a HANDOVER comment (schema below),
   swap `lens:voice` → `lens:bridge`. If the ticket ALREADY had a bridge→voice handover
   earlier (ping-pong guard), label `needs-owner` instead and summarize both analyses.
3. **Unclear / can't reproduce** → label `needs-owner` and post TWO things: (a) your analysis
   for the owner, in English; (b) a short, friendly draft reply to the REPORTER asking for the
   missing specifics — written in the reporter's language, ready for the owner to approve.
4. **Not a bug** (works as designed / user error / config) → explain why, label `needs-owner`
   with a one-line close recommendation and, when useful, a drafted how-to reply in the
   reporter's language.

Always remove the `new` label at the start of your run.

## Handover comment schema (voice → bridge)

```
### Handover: lens:voice → lens:bridge
- **Symptom:** <one sentence>
- **Evidence:** <the canonical command sent + the bridge's response/echo; log lines; trace slice>
- **Catalog:** pinned <version from metadata> vs live <if determinable>
- **Ruled out (voice):** <what you verified is correct on the voice side>
- **Bundle:** <link>
```

The bridge lens reads THIS comment first, not the raw bundle.

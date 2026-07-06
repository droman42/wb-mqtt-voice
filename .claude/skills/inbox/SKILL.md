---
name: inbox
description: Review the problem-report queue one item at a time — fix PRs and owner-escalated tickets from wb-user-reports (ARCH-33). Invoke when the user asks to review reports, check the inbox, or triage the queue, or when a session-start reminder flags pending items.
---

# /inbox — problem-report owner review

The interactive review loop for the problem-reporting system (ARCH-30 design
`docs/design/problem_reports.md` §8). Reports land as tickets in the **private**
`droman42/wb-user-reports` repo; a GitHub-hosted Claude triages each one and leaves it in one of
two states that need the owner: a **fix PR open on this repo**, or an **escalated ticket**
(`needs-owner`). This skill walks that queue **one item at a time**, with the owner deciding each.

The reports repo is the source of truth for the queue — not this repo's PR list. Every actionable
item has a `wb-user-reports` ticket; a fix PR is linked from its ticket.

## 1. Gather the queue

Two buckets, voice lens only (the bridge twin is the bridge repo's `/inbox`):

```bash
# fix PRs awaiting review (ticket carries the PR link)
gh issue list --repo droman42/wb-user-reports --label fix-pr-open --label lens:voice \
  --state open --json number,title,url

# escalations awaiting an owner decision or reply
gh issue list --repo droman42/wb-user-reports --label needs-owner --label lens:voice \
  --state open --json number,title,url
```

If both are empty: say the inbox is clear and stop. Otherwise report the count and start the walk.

## 2. Walk one item at a time

Never batch. For each ticket, present it, do the reading, recommend, then **wait for the owner's
decision before touching anything**. Move to the next only when the current one is resolved or the
owner says skip.

### A `fix-pr-open` ticket

1. Read the ticket + the triage comment (`gh issue view <n> --repo droman42/wb-user-reports --comments`).
2. Open the linked PR here (`gh pr view <pr> --json title,body,files,additions,deletions`;
   `gh pr diff <pr>`).
3. **Verify the finding independently — do not trust the triage.** The cloud triage reasons from a
   bundle it cannot re-run against live hardware, and a report is often triggered by a transient or
   a dev-session artifact (e.g. a process kill mid-run reads like a crash). Reproduce or refute:
   run the affected tests, read the cited code, check whether the failure is real and whether the
   fix is at the right altitude (the repo's CLAUDE.md discipline — donation/pattern fixes before
   handler special-cases, etc.).
4. Give a plain verdict: **merge / revise / reject**, with the one reason that decides it.
5. On the owner's call:
   - **merge** → `gh pr merge <pr> --squash` (or their preferred strategy); then close the ticket
     with a note (`gh issue close <n> --repo droman42/wb-user-reports --comment "..."`) and, if the
     work belongs in the ledger as its own task, file it per `every-task-in-the-ledger`.
   - **revise** → make the changes on the PR branch (or ask triage to, via a ticket comment), push,
     re-review.
   - **reject** → `gh pr close <pr>` + close the ticket explaining why (a false positive is a normal
     outcome; record it so the pattern is visible).

### A `needs-owner` ticket

1. Read the ticket + triage comment. Triage escalates for a decision OR because the reporter needs
   more information (v1 has no user registry, so unclear reports always come here — usually with a
   **drafted reply in the reporter's language** ready for approval).
2. If a reply is drafted: present it, let the owner approve/edit, then post it as a ticket comment.
   The reporter has no GitHub account — the reply is for the owner's own out-of-band relay (the
   registry that closes this loop is a later release).
3. If it's a decision (dedup, not-a-bug, needs-bridge-handover): recommend, act on the owner's call
   (comment, relabel `lens:bridge` for a handover, or close), one line of reasoning.

## 3. Close out

After the walk, summarize what changed (merged / rejected / replied / handed over / skipped). Leave
anything the owner deferred in place — the queue is durable; it'll resurface next `/inbox`.

## Notes

- **Leak fence still applies here.** Ticket bundles carry household data (logs, rooms, config); this
  repo's PRs and commits must stay technical. Don't paste bundle contents into a public PR or commit
  message.
- **Read-only is safe.** Listing and reading (steps 1–2) touch nothing. Only merges, closes,
  comments, and pushes change state, and each waits for an explicit owner decision.

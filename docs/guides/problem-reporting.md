# Problem reporting

Something misbehaved? Tell Irene: **«сообщи о проблеме»** (or "report a problem"). She'll ask you
to describe it in your own words, package everything a developer needs alongside your
description, and file it — no account, no forms, no screenshots.

![Problem reporting flow](../images/problem-report-flow.png)

## How the conversation goes

- **You:** «сообщи о проблеме»
- **Irene:** «Опишите проблему своими словами.»
- **You:** anything at all — «таймер не сработал утром», «свет в спальне не включается»

That second phrase matters: whatever you say next is taken **as the description**, even if it
sounds exactly like a command. Irene deliberately doesn't act on it — she records it. Changed
your mind? Say «отмена» (or «не важно»). Say nothing for about a minute and a half and the
report quietly evaporates — the next thing you say is treated as a normal command again, no
nagging.

If you're offline when the report is ready, Irene says so and keeps trying in the background —
the promise survives even a restart. You'll hear a short confirmation when it eventually goes
through.

## What gets sent

Alongside your description: the day's log, the recent conversation turns, a synopsis of the
last few requests (what was heard, what was understood, what happened), any recently running
or failed background actions, and your configuration — **with every key, token and password
scrubbed out first**. No audio recordings are ever included.

If Irene is [connected to your smart home](smart-home.md), the report also carries the home's
side of the story: the bridge contributes its own snapshot — recent device commands, live
device states, and what actually went over the wire — scrubbed the same way. So «свет в
спальне не включается» arrives with the evidence of whether the command reached the lamp. And
if the bridge itself can't be reached at that moment, that fact is recorded in the report too —
it's often exactly the clue that's needed.

Where it goes matters: reports are filed into a **private** repository that only the project
owner (and the automation that analyzes reports) can see. They are never posted publicly, and
the raw bundles are automatically deleted after 30 days. There's also a politeness valve: at
most a few reports per hour — if you hit it, Irene asks for a little patience.

## Setting it up

Reporting is off by default (Irene will say so honestly if asked to report). To enable it you
need a **private** GitHub repository to receive the reports and a fine-grained personal access
token scoped to *that repository only*, with Issues and Contents write permission.

```toml
[reports]
enabled = true
repo = "you/your-reports-repo"       # must be PRIVATE — bundles contain logs and config
token_env = "IRENE_REPORTS_TOKEN"    # the env variable holding the token
```

Put the token in the environment (e.g. your `.env`), never in the config file:

```bash
IRENE_REPORTS_TOKEN=github_pat_...
```

With the repo or token missing, Irene starts normally and reporting simply stays off.

## What happens to a report

Each report becomes a ticket in the reports repository, where an automated analyst reads the
bundle, tries to reproduce the problem, and either proposes a fix for the maintainer's review
or asks a follow-up — in the language you wrote your description in. The heavier the detail in
your description (what you said, what you expected, what happened instead), the shorter that
loop gets.

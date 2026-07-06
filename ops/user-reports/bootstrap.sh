#!/bin/sh
# One-shot bootstrap of the wb-user-reports repo (BUILD-12, design docs/design/problem_reports.md).
# RUN BY THE OWNER (creates a repo on your account). Idempotent. Prereq: gh authenticated.
# Usage: cd wb-mqtt-voice/ops/user-reports && bash bootstrap.sh [owner/name]
set -eu
REPO="${1:-droman42/wb-user-reports}"
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1. Private repo
gh repo view "$REPO" >/dev/null 2>&1 || gh repo create "$REPO" --private \
  --description "Private intake for Irene/bridge problem reports (tickets + bundles)"

# 2. Labels (design §5/§7): the ticket state machine + lenses
for spec in \
  "problem-report|d73a4a|Filed by a device/UI reporter" \
  "lens:voice|1d76db|Triage against wb-mqtt-voice" \
  "lens:bridge|0e8a16|Triage against wb-mqtt-bridge" \
  "new|fbca04|Not yet triaged" \
  "needs-owner|b60205|Waiting for the owner's decision/reply" \
  "fix-pr-open|5319e7|A fix PR is open on a code repo"; do
  name=$(printf %s "$spec" | cut -d'|' -f1)
  color=$(printf %s "$spec" | cut -d'|' -f2)
  desc=$(printf %s "$spec" | cut -d'|' -f3)
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" 2>/dev/null \
    || gh label edit "$name" --repo "$REPO" --color "$color" --description "$desc"
done

# 3. Content (README + workflows + lens process files)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone "https://github.com/$REPO" "$TMP/repo" 2>/dev/null || git init -b main "$TMP/repo"
cp -r "$HERE/README.md" "$HERE/.github" "$TMP/repo/"
cd "$TMP/repo"
git add -A
if ! git diff --cached --quiet; then
  git commit -m "bootstrap: triage + retention workflows, lens process files (BUILD-12)"
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$REPO"
  git push -u origin main
fi

# 4. The owner-actions issue (the clicks no script can do)
if ! gh issue list --repo "$REPO" --search "Bootstrap: owner actions" --json number --jq '.[0].number' | grep -q .; then
  gh issue create --repo "$REPO" --title "Bootstrap: owner actions" --body "$(cat <<'BODY'
Finish the setup (one-time):

- [ ] **Install the Claude GitHub App** on THREE repos: `wb-user-reports`, `wb-mqtt-voice`,
      `wb-mqtt-bridge` (github.com/apps/claude → Configure).
- [ ] **Set the Claude OAuth secret** here: run `claude setup-token` locally, then add the
      result as repo secret `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets → Actions).
- [ ] **Mint the cross-repo PAT**: fine-grained PAT, repos `wb-mqtt-voice` + `wb-mqtt-bridge`,
      permissions Contents+Pull requests (write). Add here as secret `REPORTS_CROSS_REPO_TOKEN`
      (lets triage open fix PRs on the public repos).
- [ ] **Mint the device PAT**: fine-grained PAT, repo `wb-user-reports` ONLY, permissions
      Issues+Contents (write). Put it on each Irene device as env `IRENE_REPORTS_TOKEN`, and
      set `[reports] enabled = true` + `repo = "droman42/wb-user-reports"` in its config.
- [ ] **Smoke test**: say «сообщи о проблеме», describe something — a ticket should appear
      here and triage should run on it.
BODY
)"
fi
echo "✅ $REPO bootstrapped. Finish the checklist in the 'Bootstrap: owner actions' issue."

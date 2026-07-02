#!/bin/sh
# Update Irene on the controller (BUILD-10, design D-5). Run after `git pull`:
#   cd /mnt/data/wb-mqtt-voice && git pull && ./ops/update.sh
#
# 1. Sync the GIT-OWNED assets content (donations/localization/prompts/templates/web +
#    the donation contract schemas) from the checkout into the writable assets mount.
#    --delete keeps each synced subtree exactly matching the repo; the enumeration is
#    EXPLICIT so runtime-owned subtrees (models/ cache/ state/ traces/ credentials/
#    temp/) are never touched — that's where downloaded models and durable action
#    records live (never delete them on update).
# 2. Pull fresh images and restart; prune old untagged layers (WB flash is small).
set -eu
cd "$(dirname "$0")"

ASSETS_DIR="${ASSETS_DIR:-../.assets}"
mkdir -p "$ASSETS_DIR"

for d in donations localization prompts templates web; do
    rsync -a --delete "../assets/$d/" "$ASSETS_DIR/$d/"
done
cp ../assets/donation_contract_v1.1.json ../assets/donation_language_v1.1.json "$ASSETS_DIR/"
echo "assets synced -> $ASSETS_DIR"

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f
docker compose ps

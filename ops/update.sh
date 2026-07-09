#!/bin/sh
# Update Irene on the controller (BUILD-10, design D-5). Run after `git pull`:
#   cd /mnt/sdcard/wb-mqtt-voice && git pull && ./ops/update.sh
#
# The clone (on the SD card) is the delivery vehicle; the containers mount the
# runtime tree at /mnt/data/mqtt-voice-config (same split as the sibling
# mqtt-bridge-config). This script bridges the two:
#
# 1. Sync the GIT-OWNED assets content (donations/localization/prompts/templates/web +
#    the donation contract schemas) from the clone into the runtime assets tree.
#    --delete keeps each synced subtree exactly matching the repo; the enumeration is
#    EXPLICIT so runtime-owned subtrees (models/ cache/ state/ traces/ credentials/
#    temp/) are never touched — that's where downloaded models and durable action
#    records live (never delete them on update).
# 2. Pull fresh images and restart; prune old untagged layers (WB flash is small).
set -eu
cd "$(dirname "$0")"

RUNTIME_DIR="${RUNTIME_DIR:-/mnt/data/mqtt-voice-config}"
ASSETS_DIR="$RUNTIME_DIR/assets"
LOGS_DIR="$RUNTIME_DIR/logs"
CONFIG_DIR="$RUNTIME_DIR/config"
PROFILE_FILE="$RUNTIME_DIR/config-profile"
mkdir -p "$ASSETS_DIR" "$LOGS_DIR" "$CONFIG_DIR"

# Which profile TOML this controller runs (must match the image variant):
# embedded-armv7 (WB7, default) | embedded-aarch64 (WB8.5/Pi) | *-en variants.
#
# The choice STICKS. Passing CONFIG_PROFILE=... records it in the runtime tree; every later run
# reuses it. Otherwise a plain `./update.sh` on a WB8.5 would silently re-deliver the armv7
# profile over irene.toml — a config/image mismatch nothing detects.
if [ -z "${CONFIG_PROFILE:-}" ]; then
    if [ -f "$PROFILE_FILE" ]; then
        CONFIG_PROFILE="$(cat "$PROFILE_FILE")"
    else
        CONFIG_PROFILE=embedded-armv7
    fi
fi
# Validate BEFORE recording, or a typo would persist and break every later run.
[ -f "../configs/$CONFIG_PROFILE.toml" ] || {
    echo "error: unknown CONFIG_PROFILE '$CONFIG_PROFILE' (no configs/$CONFIG_PROFILE.toml)" >&2
    echo "       expected one of: $(cd ../configs && echo embedded-*.toml | sed 's/\.toml//g')" >&2
    exit 2
}
printf '%s\n' "$CONFIG_PROFILE" > "$PROFILE_FILE"

# THE REPO OWNS THE CONFIG (bridge semantics): delivered on every update, on-box
# edits are overwritten — config changes are made in the repo and arrive by git pull.
cp "../configs/$CONFIG_PROFILE.toml" "$CONFIG_DIR/irene.toml"
echo "config delivered -> $CONFIG_DIR/irene.toml ($CONFIG_PROFILE)"

for d in donations localization prompts templates web; do
    rsync -a --delete "../assets/$d/" "$ASSETS_DIR/$d/"
done
cp ../assets/donation_contract_v1.1.json ../assets/donation_language_v1.1.json "$ASSETS_DIR/"

# The container runs non-root as uid 1000 (`USER domovoy` in the Dockerfiles); on the
# controller this script runs as root, so the mounted tree must be handed to that uid or the
# first model download / log write fails with EACCES. The uid is the contract — the name
# exists only inside the container, and uid 1000 is unassigned on a stock Wirenboard.
chown -R 1000:1000 "$ASSETS_DIR" "$LOGS_DIR" 2>/dev/null || true
echo "assets synced -> $ASSETS_DIR"

# Deploy the compose file into the runtime tree and run compose FROM there — boot
# must not depend on the SD card (the bridge's reboot lesson: the card is a lazy
# automount; a unit rooted on it dies at boot before the card enumerates). The
# runtime tree is also where compose finds .env (user-created, never touched here).
cp docker-compose.yml "$RUNTIME_DIR/docker-compose.yml"
cd "$RUNTIME_DIR"

docker compose pull
docker compose up -d --remove-orphans
docker image prune -f
docker compose ps

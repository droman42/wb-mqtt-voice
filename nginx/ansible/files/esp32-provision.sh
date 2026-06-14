#!/usr/bin/env bash
# esp32-provision.sh — operator CLI for the ESP32 CSR-approval flow (ARCH-22 Plane B, D-17).
#   esp32-provision list                  show pending CSRs (client_id + subject + pubkey fingerprint)
#   esp32-provision approve <client_id>   review + sign with the home CA -> publish the cert
#   esp32-provision revoke  <client_id>   drop a pending CSR
#   esp32-provision status                counts
set -euo pipefail

SRV_DIR="${SRV_DIR:-/srv/esp32}"
PEND="$SRV_DIR/provision/pending"
CERTS="$SRV_DIR/provision/cert"

usage() {
  echo "usage: esp32-provision {list|approve <client_id>|revoke <client_id>|status}" >&2
  exit 1
}

valid_id() { [[ "$1" =~ ^[A-Za-z0-9_-]+$ ]]; }

csr_info() {  # <csr-file>  -> subject + sha256 fingerprint of the public key
  local f="$1" subj fp
  subj="$(openssl req -in "$f" -noout -subject 2>/dev/null | sed 's/^subject= *//')"
  fp="$(openssl req -in "$f" -noout -pubkey 2>/dev/null \
        | openssl pkey -pubin -outform DER 2>/dev/null \
        | openssl dgst -sha256 2>/dev/null | awk '{print $NF}')"
  printf '  subject:       %s\n  pubkey-sha256: %s\n' "${subj:-?}" "${fp:-?}"
}

cmd="${1:-}"
shift || true
case "$cmd" in
  list)
    shopt -s nullglob
    found=0
    for f in "$PEND"/*.csr; do
      found=1
      printf 'PENDING  %s\n' "$(basename "$f" .csr)"
      csr_info "$f"
    done
    [[ "$found" -eq 0 ]] && echo "(no pending CSRs)"
    ;;
  approve)
    id="${1:-}"; { [[ -n "$id" ]] && valid_id "$id"; } || usage
    [[ -f "$PEND/$id.csr" ]] || { echo "no pending CSR for '$id'" >&2; exit 3; }
    echo "Reviewing CSR for '$id':"
    csr_info "$PEND/$id.csr"
    SRV_DIR="$SRV_DIR" esp32-sign-csr.sh "$id"
    ;;
  revoke)
    id="${1:-}"; valid_id "${id:-}" || usage
    rm -f "$PEND/$id.csr" && echo "dropped pending CSR for '$id'"
    ;;
  status)
    p="$(find "$PEND" -maxdepth 1 -name '*.csr' 2>/dev/null | wc -l)"
    c="$(find "$CERTS" -maxdepth 1 -name '*.crt' 2>/dev/null | wc -l)"
    echo "pending: $p | issued: $c"
    ;;
  *)
    usage
    ;;
esac

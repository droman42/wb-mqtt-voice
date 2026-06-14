#!/usr/bin/env bash
# esp32-sign-csr.sh <client_id> — sign one pending device CSR with the home CA (clientAuth).
# Treats the CSR as UNTRUSTED input: client_id is validated, the CSR is signed by file (never
# interpolated into a shell). ARCH-22 Plane B.
set -euo pipefail

CA_DIR="${CA_DIR:-/etc/esp32-ca}"
SRV_DIR="${SRV_DIR:-/srv/esp32}"
CERT_DAYS="${CERT_DAYS:-825}"

id="${1:-}"
if [[ ! "$id" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "error: invalid client_id '$id' (allowed: A-Za-z0-9_-)" >&2
  exit 2
fi

csr="$SRV_DIR/provision/pending/$id.csr"
out="$SRV_DIR/provision/cert/$id.crt"
[[ -f "$csr" ]] || { echo "error: no pending CSR at $csr" >&2; exit 3; }

# it must parse + self-verify as a CSR before we sign anything
if ! openssl req -in "$csr" -noout -verify >/dev/null 2>&1; then
  echo "error: $csr is not a valid CSR" >&2
  exit 4
fi

ext="$(mktemp)"
trap 'rm -f "$ext"' EXIT
cat > "$ext" <<EOF
basicConstraints=CA:FALSE
keyUsage=digitalSignature
extendedKeyUsage=clientAuth
EOF

openssl x509 -req -in "$csr" -CA "$CA_DIR/ca.crt" -CAkey "$CA_DIR/ca.key" -CAcreateserial \
  -days "$CERT_DAYS" -sha256 -extfile "$ext" -out "$out"
chmod 644 "$out"

echo "signed: $out (valid ${CERT_DAYS}d)"
# the device fetches its cert from /esp32/provision/cert/$id.crt; drop the consumed CSR
rm -f "$csr"

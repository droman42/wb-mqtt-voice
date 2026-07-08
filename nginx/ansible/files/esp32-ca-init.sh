#!/usr/bin/env bash
# esp32-ca-init.sh — create the ESP32 home CA + the WB7 server cert (idempotent).
# EC prime256v1 throughout (light for the device's mTLS handshake). ARCH-22 Plane B.
set -euo pipefail

CA_DIR="${CA_DIR:-/etc/esp32-ca}"
SRV_DIR="${SRV_DIR:-/srv/esp32}"
CA_CN="${CA_CN:-HomeVoice ESP32 CA}"
SERVER_CN="${SERVER_CN:-assistant.lan}"
SERVER_SANS="${SERVER_SANS:-DNS:assistant.lan}"
CA_DAYS="${CA_DAYS:-3650}"
CERT_DAYS="${CERT_DAYS:-825}"

umask 077
mkdir -p "$CA_DIR" \
         "$SRV_DIR/provision/pending" "$SRV_DIR/provision/cert" \
         "$SRV_DIR/firmware" "$SRV_DIR/models"

# --- home CA (never overwritten) -------------------------------------------------
if [[ -f "$CA_DIR/ca.key" ]]; then
  echo "CA already present at $CA_DIR/ca.key — leaving it untouched."
else
  echo "Generating home CA (EC prime256v1, CN=${CA_CN}) ..."
  openssl ecparam -name prime256v1 -genkey -noout -out "$CA_DIR/ca.key"
  openssl req -x509 -new -key "$CA_DIR/ca.key" -sha256 -days "$CA_DAYS" \
    -subj "/CN=${CA_CN}" -out "$CA_DIR/ca.crt"
  chmod 600 "$CA_DIR/ca.key"
  chmod 644 "$CA_DIR/ca.crt"
fi

# publish the PUBLIC CA cert for the :8081 bootstrap zone (device trust anchor)
install -m644 "$CA_DIR/ca.crt" "$SRV_DIR/provision/ca.crt"

# --- WB7 server cert (never overwritten) -----------------------------------------
if [[ -f "$CA_DIR/server.key" ]]; then
  echo "Server cert already present — leaving it untouched."
else
  echo "Generating WB7 server cert (CN=${SERVER_CN}, SAN=${SERVER_SANS}) ..."
  openssl ecparam -name prime256v1 -genkey -noout -out "$CA_DIR/server.key"
  openssl req -new -key "$CA_DIR/server.key" -subj "/CN=${SERVER_CN}" -out "$CA_DIR/server.csr"
  cat > "$CA_DIR/server.ext" <<EOF
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=${SERVER_SANS}
EOF
  openssl x509 -req -in "$CA_DIR/server.csr" -CA "$CA_DIR/ca.crt" -CAkey "$CA_DIR/ca.key" \
    -CAcreateserial -days "$CERT_DAYS" -sha256 -extfile "$CA_DIR/server.ext" -out "$CA_DIR/server.crt"
  chmod 600 "$CA_DIR/server.key"
  chmod 644 "$CA_DIR/server.crt"
  rm -f "$CA_DIR/server.csr" "$CA_DIR/server.ext"
fi

echo "esp32-ca-init: done."

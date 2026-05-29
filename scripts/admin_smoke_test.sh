#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
  echo "Missing .env. Start the interface first."
  exit 1
fi

set -a
source .env
set +a

echo "[1] Health"
curl -fsS http://localhost:9530/health
echo
echo

echo "[2] UI"
curl -fsS http://localhost:9530/ui >/dev/null
echo "UI loads"
echo

echo "[3] Admin audit access"
curl -fsS -H "Authorization: Bearer $SARA_ADMIN_TOKEN" \
  "http://localhost:9530/v1/audit?limit=50"
echo
echo

echo "[4] Operator blocked from admin audit"
STATUS="$(curl -s -o /tmp/sara_audit_denied.txt -w "%{http_code}" \
  -H "Authorization: Bearer $SARA_RELAY_TOKEN" \
  "http://localhost:9530/v1/audit?limit=50")"

if [ "$STATUS" != "403" ]; then
  echo "Expected 403, got $STATUS"
  cat /tmp/sara_audit_denied.txt
  exit 1
fi

echo "Operator correctly blocked from admin audit."
echo

echo "[5] Relay"
curl -fsS -X POST http://localhost:9530/v1/relay \
  -H "Authorization: Bearer $SARA_RELAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target":"SSPADAWANZZ","message":"ACCESS Sara_Pro"}'
echo
echo

echo "integration_ok"

#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:9530}"
TOKEN="${SARA_ADMIN_TOKEN:-}"
if [ -f .env ] && [ -z "$TOKEN" ]; then
  TOKEN="$(grep -E '^SARA_ADMIN_TOKEN=' .env | tail -1 | cut -d= -f2- | tr -d '"' || true)"
fi
if [ -z "$TOKEN" ]; then
  echo "ERROR: SARA_ADMIN_TOKEN not found in environment or .env" >&2
  exit 1
fi

echo "[1] WORLD status"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $TOKEN" "$BASE/world/status" | python -m json.tool

echo "[2] WORLD parse"
curl -fsS -X POST -H "Content-Type: application/json" -H "X-SARA-ADMIN-TOKEN: $TOKEN" \
  -d '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}' \
  "$BASE/world/command/parse" | python -m json.tool

echo "[3] WORLD simulate structured"
curl -fsS -X POST -H "Content-Type: application/json" -H "X-SARA-ADMIN-TOKEN: $TOKEN" \
  -d '{"intent":"PATCH","target":"REGISTRY","action":"patch","scope":"SARA_CORE","mode":"DRY_RUN","reason":"smoke test","payload":{"demo":true}}' \
  "$BASE/world/command/simulate" | python -m json.tool

echo "[4] WORLD audit"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $TOKEN" "$BASE/world/audit?limit=10" | python -m json.tool

echo "WORLD CONTROLLER smoke test passed"

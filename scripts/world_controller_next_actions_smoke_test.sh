#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN="$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)"
BASE="http://127.0.0.1:9530"
HDR=(-H "X-SARA-ADMIN-TOKEN: $ADMIN" -H "Content-Type: application/json")
BODY='{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}'

echo "[1] GET /world/preflight"
curl -fsS "${HDR[@]}" "$BASE/world/preflight" | python3 -m json.tool >/dev/null

echo "[2] POST /world/preflight/watchers"
curl -fsS -X POST "${HDR[@]}" "$BASE/world/preflight/watchers" | python3 -m json.tool >/dev/null

echo "[3] POST /world/preflight/guardians"
curl -fsS -X POST "${HDR[@]}" --data "$BODY" "$BASE/world/preflight/guardians" | python3 -m json.tool >/dev/null

echo "[4] POST /world/preflight/oracle"
curl -fsS -X POST "${HDR[@]}" --data "$BODY" "$BASE/world/preflight/oracle" | python3 -m json.tool >/dev/null

echo "[5] POST /world/preflight/ark"
curl -fsS -X POST "${HDR[@]}" "$BASE/world/preflight/ark" | python3 -m json.tool >/dev/null

echo "[6] POST /world/preflight/run"
curl -fsS -X POST "${HDR[@]}" --data "$BODY" "$BASE/world/preflight/run" | python3 -m json.tool >/dev/null

echo "[7] GET /world/evidence/preflight"
curl -fsS "${HDR[@]}" "$BASE/world/evidence/preflight" | python3 -m json.tool >/dev/null

echo "WORLD CONTROLLER next-actions preflight smoke test passed"

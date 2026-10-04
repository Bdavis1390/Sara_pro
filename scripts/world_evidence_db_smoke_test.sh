#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN="${ADMIN:-$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)}"
BASE="${BASE:-http://127.0.0.1:9530}"
echo "[1] memory init"
curl -fsS -X POST -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/memory/init" | python3 -m json.tool >/dev/null
echo "[2] memory stats"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/memory/stats" | python3 -m json.tool >/dev/null
echo "[3] memory ingest"
curl -fsS -X POST -H "X-SARA-ADMIN-TOKEN: $ADMIN" -H "Content-Type: application/json" -d '{"force": false, "limit": 1000}' "$BASE/world/memory/ingest" | python3 -m json.tool >/dev/null
echo "[4] memory search"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/memory/search?q=Worldshepherd" | python3 -m json.tool >/dev/null
echo "[5] memory projects"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/memory/projects" | python3 -m json.tool >/dev/null
echo "[6] memory verify"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/memory/verify" | python3 -m json.tool >/dev/null
echo "WORLD CONTROLLER persistent evidence DB smoke test passed"

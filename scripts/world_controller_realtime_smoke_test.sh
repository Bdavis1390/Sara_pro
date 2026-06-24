#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN="$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)"
BASE="http://127.0.0.1:9530"
echo "[1] realtime scan"; curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/realtime/scan" | python3 -m json.tool >/dev/null
echo "[2] realtime dashboard dossier"; curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/realtime/panel/dashboard" | python3 -m json.tool >/dev/null
echo "[3] realtime projects"; curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/realtime/projects" | python3 -m json.tool >/dev/null
echo "[4] realtime documents"; curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE/world/realtime/documents?limit=20" | python3 -m json.tool >/dev/null
echo "WORLD CONTROLLER realtime project/document smoke test passed"

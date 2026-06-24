#!/usr/bin/env bash
set -euo pipefail
cd "${1:-$HOME/Sara_pro}"
ADMIN="$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)"
BASE="http://127.0.0.1:9530"
H=(-H "X-SARA-ADMIN-TOKEN: $ADMIN")

json_get() {
  local label="$1"
  local path="$2"
  echo "$label"
  curl -fsS "${H[@]}" "$BASE$path" | python3 -m json.tool >/tmp/world_evidence_test.json
  python3 - <<'PY'
import json
p='/tmp/world_evidence_test.json'
data=json.load(open(p))
assert data.get('ok') is not False, data
print('  ok:', data.get('panel') or data.get('service') or data.get('title'))
PY
}

json_get "[1] Evidence index" "/world/evidence"
json_get "[2] Registry dossier" "/world/registry"
HASH="$(curl -fsS "${H[@]}" "$BASE/world/registry" | python3 -c 'import sys,json; print(json.load(sys.stdin)["registry_hash"])')"
json_get "[3] Registry hash evidence" "/world/evidence/registry/hash/$HASH"
json_get "[4] Node evidence" "/world/evidence/node/SARA_CORE"
SNAP="$(curl -fsS -X POST "${H[@]}" "$BASE/world/ark/snapshot" | python3 -c 'import sys,json; print(json.load(sys.stdin)["snapshot_id"])')"
json_get "[5] Ark evidence" "/world/evidence/ark/$SNAP"
AUD="$(curl -fsS "${H[@]}" "$BASE/world/audit?limit=10" | python3 -c 'import sys,json; rows=json.load(sys.stdin).get("records",[]); print(rows[0]["audit_id"] if rows else "")')"
if [ -n "$AUD" ]; then
  json_get "[6] Audit evidence" "/world/evidence/audit/$AUD"
fi

echo "WORLD CONTROLLER evidence-link dossier smoke test passed"

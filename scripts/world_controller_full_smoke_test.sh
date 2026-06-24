#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:9530}"
cd "${REPO:-$HOME/Sara_pro}"
ADMIN="${SARA_ADMIN_TOKEN:-$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)}"

if [ -z "$ADMIN" ]; then
  echo "SARA_ADMIN_TOKEN missing. Check .env" >&2
  exit 1
fi

call_get() {
  local label="$1" path="$2"
  echo "[$label] GET $path"
  curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" "$BASE$path" | python3 -m json.tool >/tmp/world_smoke_${label}.json
}

call_post() {
  local label="$1" path="$2" body="$3"
  echo "[$label] POST $path"
  curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN" -H 'Content-Type: application/json' -d "$body" "$BASE$path" | python3 -m json.tool >/tmp/world_smoke_${label}.json
}

call_get 1 /world/status
call_get 2 /world/dashboard
call_get 3 /world/watchers
call_get 4 /world/guardians
call_get 5 /world/oracle
call_get 6 /world/ark
call_get 7 /world/registry
call_get 8 '/world/audit?limit=10'
call_get 9 /world/admin
call_post 10 /world/command/parse '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}'
call_post 11 /world/guardians/classify '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}'
call_post 12 /world/oracle/simulate '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}'
call_post 13 /world/command/simulate '{"intent":"PATCH","target":"REGISTRY","action":"patch","scope":"SARA_CORE","mode":"DRY_RUN","reason":"full smoke test","payload":{"demo":true}}'
call_post 14 /world/command/execute '{"intent":"CONFIGURE","target":"ORACLE_ENGINE","action":"set_mode","scope":"local","mode":"EXECUTE","reason":"safe blue smoke test","payload":{"mode":"simulate_first"},"execute_confirm":true}'
call_post 15 /world/registry/patch '{"node_id":"WATCHER_GRID","status":"online","role":"telemetry","guardian_policy":"GREEN","capabilities":["observe","health","heartbeat"],"note":"full smoke test"}'
call_post 16 /world/ark/snapshot '{}'

echo "WORLD CONTROLLER full controls smoke test passed"
echo "Open: $BASE/world/ui"

#!/usr/bin/env bash
set -euo pipefail
cd "${1:-$HOME/Sara_pro}"
ADMIN="$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)"
if [ -z "$ADMIN" ]; then
  echo "SARA_ADMIN_TOKEN missing in .env" >&2
  exit 1
fi
hdr=(-H "X-SARA-ADMIN-TOKEN: $ADMIN")

echo "[1] UI contains dossier renderer"
curl -fsS http://127.0.0.1:9530/world/ui | grep -q "Dossier Console"
curl -fsS http://127.0.0.1:9530/world/ui | grep -q "renderDossier"

echo "[2] Core dossier source endpoints"
for path in \
  /world/status \
  /world/dashboard \
  /world/watchers \
  /world/guardians \
  /world/oracle \
  /world/ark \
  /world/registry \
  /world/audit?limit=10 \
  /world/admin
  do
    echo "    GET $path"
    curl -fsS "${hdr[@]}" "http://127.0.0.1:9530$path" | python3 -m json.tool >/dev/null
  done

echo "[3] Command dossier source endpoints"
curl -fsS "${hdr[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}' \
  http://127.0.0.1:9530/world/command/parse | python3 -m json.tool >/dev/null
curl -fsS "${hdr[@]}" -H 'Content-Type: application/json' \
  -d '{"text":"SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN"}' \
  http://127.0.0.1:9530/world/oracle/simulate | python3 -m json.tool >/dev/null

echo "WORLD CONTROLLER dossier UI smoke test passed"

#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${SARA_BASE_URL:-http://127.0.0.1:9530}"
: "${SARA_RELAY_TOKEN:?SARA_RELAY_TOKEN is required}"
: "${SARA_ADMIN_TOKEN:?SARA_ADMIN_TOKEN is required}"

json_header=(-H 'Content-Type: application/json')
relay_auth=(-H "Authorization: Bearer ${SARA_RELAY_TOKEN}")
admin_auth=(-H "Authorization: Bearer ${SARA_ADMIN_TOKEN}")

printf '[1] Compatibility health\n'
curl --fail --silent --show-error "${BASE_URL}/health"
printf '\n\n[2] Liveness and readiness\n'
curl --fail --silent --show-error "${BASE_URL}/livez"
printf '\n'
curl --fail --silent --show-error "${BASE_URL}/readyz"

printf '\n\n[3] UI\n'
curl --fail --silent --show-error "${BASE_URL}/ui" | grep -q 'Worldshepherd SARA'
echo 'UI loads'

printf '\n[4] Relay action\n'
curl --fail --silent --show-error "${relay_auth[@]}" "${json_header[@]}" \
  -d '{"target":"SSPADAWANZZ","action":"deployment_smoke_test","payload":{"scope":"local"}}' \
  "${BASE_URL}/v1/relay"

printf '\n\n[5] Relay token blocked from every admin endpoint\n'
for endpoint in /v1/audit /admin/registry /admin/selftest; do
  status="$(curl --silent --output /dev/null --write-out '%{http_code}' "${relay_auth[@]}" "${BASE_URL}${endpoint}")"
  [[ "$status" == "403" ]] || { echo "Expected 403 from ${endpoint}, received $status" >&2; exit 1; }
done
status="$(curl --silent --output /dev/null --write-out '%{http_code}' -X PATCH \
  "${relay_auth[@]}" "${json_header[@]}" -d '{"values":{}}' "${BASE_URL}/admin/registry")"
[[ "$status" == "403" ]] || { echo "Expected 403 from PATCH /admin/registry, received $status" >&2; exit 1; }
echo 'Role separation: OK'

printf '\n[6] Admin registry patch\n'
curl --fail --silent --show-error "${admin_auth[@]}" "${json_header[@]}" -X PATCH \
  -d '{"values":{"SARA_CORE":{"role":"core","status":"online"},"SSPADAWANZZ":{"role":"admin_operator","status":"online"}}}' \
  "${BASE_URL}/admin/registry"

printf '\n\n[7] Admin self-test\n'
curl --fail --silent --show-error "${admin_auth[@]}" "${BASE_URL}/admin/selftest"

printf '\n\n[8] Audit access\n'
curl --fail --silent --show-error "${admin_auth[@]}" "${BASE_URL}/v1/audit?limit=50"
printf '\n\nSMOKE TEST: PASS\n'

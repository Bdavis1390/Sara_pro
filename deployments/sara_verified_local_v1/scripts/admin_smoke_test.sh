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
for endpoint in /v1/audit /admin/registry /admin/poo/registry /admin/selftest; do
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

printf '\n\n[7] Protected PoO namespace cannot use generic registry patch\n'
status="$(curl --silent --output /dev/null --write-out '%{http_code}' -X PATCH \
  "${admin_auth[@]}" "${json_header[@]}" \
  -d '{"values":{"POO_TECHNICAL_REGISTRY":{"tamper":true}}}' \
  "${BASE_URL}/admin/registry")"
[[ "$status" == "403" ]] || { echo "Expected 403 for generic PoO namespace patch, received $status" >&2; exit 1; }
echo 'Protected PoO namespace: OK'

printf '\n[8] Durable PoO technical-registry commit and idempotency\n'
poo_request="$(mktemp)"
poo_response="$(mktemp)"
trap 'rm -f "$poo_request" "$poo_response"' EXIT
python3 - "$poo_request" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

STATE_SCHEMA = "WS-POO-TECHNICAL-STATE-V1"
REGISTRY_SCHEMA = "WS-POO-TECHNICAL-REGISTRY-V1"
BOOTSTRAP_SCHEMA = "WS-POO-BOOTSTRAP-COMMIT-DECISION-V1"
REQUEST_SCHEMA = "WS-POO-DURABLE-COMMIT-REQUEST-V1"

state = {
    "schema": STATE_SCHEMA,
    "asset_id": "asset:deployment-smoke",
    "claimant_id": "claimant:deployment-smoke",
    "active_poo_digest": "poo:deployment-smoke:genesis",
    "active_coc_digest": "coc:deployment-smoke:genesis",
    "control_key_fingerprint": "key:deployment-smoke",
    "title_reference": "title:deployment-smoke",
    "generation": 0,
    "source_event_type": "CLAIM",
    "previous_poo_digest": None,
    "previous_coc_digest": None,
    "legal_title_established": False,
    "live_value_authorized": False,
    "external_transfer_executed": False,
}

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

candidate_state_digest = digest(state)
empty_registry_digest = digest({"schema": REGISTRY_SCHEMA, "states": []})
candidate_registry_digest = digest({"schema": REGISTRY_SCHEMA, "states": [state]})

projection = {
    "schema": BOOTSTRAP_SCHEMA,
    "operation": "REGISTRY_BOOTSTRAP_COMMIT_READINESS",
    "asset_id": state["asset_id"],
    "source_digest": "deployment-smoke-source-v1",
    "source_status": "REGISTRY_BOOTSTRAP_COMMIT_READY_WITH_FULL_GOVERNANCE",
    "echo_state": "ECHO_POO_BOOTSTRAP_EVIDENCE_ACCEPTED",
    "prime_state": "PRIME_POO_BOOTSTRAP_COMMIT_CANDIDATE_READY",
    "sara_state": "SARA_POO_BOOTSTRAP_HUMAN_REVIEW_READY",
    "overwatch_state": "OVERWATCH_POO_BOOTSTRAP_PENDING",
    "empty_registry_verified": True,
    "ownership_evidence_ready": True,
    "coc_valid": True,
    "state_transition_ready": True,
    "registry_commit_ready": True,
    "optimistic_concurrency_checked": True,
    "optimistic_concurrency_match": True,
    "expected_registry_digest": empty_registry_digest,
    "current_registry_digest": empty_registry_digest,
    "candidate_registry_digest": candidate_registry_digest,
    "candidate_state_digest": candidate_state_digest,
    "human_approval_required": True,
    "technical_registry_committed": False,
    "durable_registry_write_authorized": False,
    "legal_title_established": False,
    "legal_title_changed": False,
    "live_value_moved": False,
    "credential_rotated": False,
    "external_transfer_executed": False,
    "claim_boundary": "INTERNAL_POO_EMPTY_REGISTRY_BOOTSTRAP_ONLY",
}
request = {
    "schema": REQUEST_SCHEMA,
    "governance_projection": projection,
    "candidate_states": [state],
    "approval_intent": "COMMIT_INTERNAL_TECHNICAL_STATE",
    "approval_reference": "deployment-smoke:local:v1",
}
Path(sys.argv[1]).write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
PY

curl --fail --silent --show-error "${admin_auth[@]}" "${json_header[@]}" \
  --data-binary "@${poo_request}" "${BASE_URL}/admin/poo/registry/commit" > "$poo_response"
cat "$poo_response"
python3 - "$poo_response" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
commit = record["commit"]
assert commit["status"] in {"COMMITTED", "ALREADY_COMMITTED"}
assert commit["durable_internal_state_committed"] is True
assert commit["legal_title_changed"] is False
assert commit["live_value_moved"] is False
assert commit["credential_rotated"] is False
assert commit["external_transfer_executed"] is False
assert record["audit_delivery"] == "DELIVERED"
assert record["claims_boundary"] == "INTERNAL_TECHNICAL_REGISTRY_COMMIT_ONLY"
PY
curl --fail --silent --show-error "${admin_auth[@]}" "${BASE_URL}/admin/poo/registry" > "$poo_response"
python3 - "$poo_response" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
registry = record["registry"]
assert len(registry["states"]) == 1
assert len(registry["commits"]) == 1
assert registry["states"][0]["asset_id"] == "asset:deployment-smoke"
assert registry["states"][0]["legal_title_established"] is False
assert registry["states"][0]["live_value_authorized"] is False
assert registry["states"][0]["external_transfer_executed"] is False
assert record["claims_boundary"] == "INTERNAL_TECHNICAL_REGISTRY_ONLY"
PY
rm -f "$poo_request" "$poo_response"
trap - EXIT
echo 'Durable PoO technical registry: OK'

printf '\n[9] Admin self-test\n'
curl --fail --silent --show-error "${admin_auth[@]}" "${BASE_URL}/admin/selftest"

printf '\n\n[10] Audit access\n'
curl --fail --silent --show-error "${admin_auth[@]}" "${BASE_URL}/v1/audit?limit=50"
printf '\n\nSMOKE TEST: PASS\n'

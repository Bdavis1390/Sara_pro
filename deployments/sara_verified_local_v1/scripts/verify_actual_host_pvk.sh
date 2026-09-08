#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

expected_branch="${WS_EXPECTED_PVK_BRANCH:-worldshepherd/pvk-v0.5-cross-project-20260906}"
shadow_port="${WS_PVK_SHADOW_PORT:-19530}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
project_name="ws_pvk_host_${stamp,,}"
evidence_root=".host-pvk-evidence"
evidence_dir="${evidence_root}/${stamp}"
base_url="http://127.0.0.1:${shadow_port}"

if [[ ! -f .env ]]; then
  echo "ERROR: .env is required for the controlled shadow deployment." >&2
  exit 1
fi

if ! [[ "$shadow_port" =~ ^[0-9]+$ ]] || (( shadow_port < 1024 || shadow_port > 65535 )); then
  echo "ERROR: WS_PVK_SHADOW_PORT must be an integer from 1024 through 65535." >&2
  exit 1
fi

current_branch="$(git branch --show-current)"
if [[ "$current_branch" != "$expected_branch" ]]; then
  echo "ERROR: Expected branch '$expected_branch' but found '$current_branch'." >&2
  exit 1
fi

if ! git diff --quiet -- . || ! git diff --cached --quiet -- .; then
  echo "ERROR: Tracked deployment subtree is dirty; host acceptance requires a clean tracked state." >&2
  exit 1
fi

git_head="$(git rev-parse HEAD)"

# Refuse to start if another process is already listening on the selected loopback port.
python3 - "$shadow_port" <<'PY_PORT'
import socket
import sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", port))
except OSError as exc:
    raise SystemExit(f"ERROR: shadow port 127.0.0.1:{port} is not available: {exc}")
finally:
    s.close()
print(f"shadow_port_available={port}")
PY_PORT

mkdir -p "$evidence_dir"
chmod 0700 "$evidence_root" "$evidence_dir"

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${SARA_ADMIN_TOKEN:?SARA_ADMIN_TOKEN must be set in .env}"
: "${SARA_RELAY_TOKEN:?SARA_RELAY_TOKEN must be set in .env}"

if [[ "$SARA_ADMIN_TOKEN" == "$SARA_RELAY_TOKEN" ]]; then
  echo "ERROR: admin and relay tokens must differ." >&2
  exit 1
fi

cleanup() {
  docker compose -p "$project_name" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

{
  echo "schema=WS-ACTUAL-HOST-PVK-ACCEPTANCE-V1"
  echo "timestamp_utc=${stamp}"
  echo "hostname=$(hostname)"
  echo "kernel=$(uname -srmo)"
  echo "os_release=$(awk -F= '$1==\"PRETTY_NAME\" {gsub(/\"/,\"\",$2); print $2}' /etc/os-release 2>/dev/null || true)"
  echo "git_branch=${current_branch}"
  echo "git_head=${git_head}"
  echo "docker_version=$(docker --version)"
  echo "compose_version=$(docker compose version)"
  echo "shadow_project=${project_name}"
  echo "shadow_base_url=${base_url}"
} > "${evidence_dir}/baseline.txt"

export SARA_HOST_PORT="$shadow_port"
export SARA_BUILD_COMMIT="$git_head"
export SARA_RELEASE_ID="PVK-HOST-${stamp}"

docker compose -p "$project_name" config --quiet
docker compose -p "$project_name" config > "${evidence_dir}/compose.rendered.PRIVATE.yaml"
chmod 0600 "${evidence_dir}/compose.rendered.PRIVATE.yaml"

docker compose -p "$project_name" build --pull | tee "${evidence_dir}/build.log"
docker compose -p "$project_name" up -d

wait_ready() {
  for attempt in $(seq 1 40); do
    if curl --fail --silent --show-error --max-time 3 "${base_url}/readyz" > "${evidence_dir}/ready.json" 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  return 1
}

if ! wait_ready; then
  echo "ERROR: shadow SARA did not become ready." >&2
  docker compose -p "$project_name" ps -a >&2
  docker compose -p "$project_name" logs --no-color --tail=150 sara >&2
  exit 1
fi

curl --fail --silent --show-error "${base_url}/health" > "${evidence_dir}/health.json"

relay_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  -H "Authorization: Bearer ${SARA_RELAY_TOKEN}" \
  "${base_url}/v1/physics/status")"
if [[ "$relay_status" != "403" ]]; then
  echo "ERROR: relay credential unexpectedly reached PVK admin status endpoint (HTTP ${relay_status})." >&2
  exit 1
fi
printf 'relay_pvk_status_http=%s\n' "$relay_status" > "${evidence_dir}/authorization.txt"

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  "${base_url}/v1/physics/status" > "${evidence_dir}/physics-status.initial.json"

# Use a concept-stage record only to prove the PVK store and API persist state.
# Host software acceptance is deliberately not represented as scientific internal-test maturity.
record_id="PHYS-HOST-${stamp}"
python3 - "$record_id" "$stamp" > "${evidence_dir}/host-record.json" <<'PY_RECORD'
import json
import sys
record_id, stamp = sys.argv[1:]
print(json.dumps({
    "schema_version": "ws-physics-record-1",
    "record_id": record_id,
    "artifact_id": "SARA-PVK-ACTUAL-HOST",
    "project_id": "SARA",
    "physics_domain": ["governance", "evidence"],
    "physics_layer": "P2_ESTABLISHED_ENGINEERING",
    "model_scope": "PVK store/API persistence probe executed during actual-host shadow acceptance",
    "assumptions": [
        "This record is a persistence probe only.",
        "It does not establish experimental validation of any Worldshepherd physical concept."
    ],
    "boundary_conditions": ["Loopback-only shadow deployment on the current Worldshepherd host"],
    "initial_conditions": [],
    "parameters": [],
    "unit_system": "SI",
    "failure_modes": [
        "PVK persistence failure",
        "authorization boundary failure",
        "claims-linter failure",
        "restart persistence failure"
    ],
    "hazard_controls": ["Shadow Compose project uses a separate port and volume; cleanup removes the shadow project."],
    "validation_state": "concept",
    "independent_review_state": "none",
    "independent_evidence_refs": [],
    "claim_label": "IMPLEMENTED IN SOFTWARE",
    "claim_class": 2,
    "external_safe_statement": "PVK actual-host acceptance is bounded software evidence; it does not validate any underlying physical-science claim.",
    "cre1aws_approval_state": "not_requested",
    "evidence_package_refs": [],
    "audit_event_ids": [],
    "created_at": stamp,
    "updated_at": stamp
}, sort_keys=True))
PY_RECORD

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary @"${evidence_dir}/host-record.json" \
  "${base_url}/admin/physics/records" > "${evidence_dir}/record-append.json"

python3 - "${evidence_dir}/lint-request.json" <<'PY_LINT'
import json
import sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({"text": "This is proven reactionless propulsion."}) + "\n", encoding="utf-8")
PY_LINT

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary @"${evidence_dir}/lint-request.json" \
  "${base_url}/admin/physics/lint" > "${evidence_dir}/lint-response.json"

python3 - "${evidence_dir}/lint-response.json" <<'PY_CHECK_LINT'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("blocked") is not True:
    raise SystemExit("claims linter did not block the reactionless-propulsion claim")
if not any(item.get("rule_id") == "PROP-01" and item.get("severity") == "BLOCK" for item in payload.get("findings", [])):
    raise SystemExit("PROP-01 BLOCK finding missing")
PY_CHECK_LINT

docker compose -p "$project_name" restart sara
if ! wait_ready; then
  echo "ERROR: shadow SARA did not recover after restart." >&2
  exit 1
fi

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  "${base_url}/v1/physics/records?limit=100&project_id=SARA" > "${evidence_dir}/physics-records.after-restart.json"

python3 - "$record_id" "${evidence_dir}/physics-records.after-restart.json" <<'PY_PERSIST'
import json
import sys
record_id, path = sys.argv[1:]
payload = json.load(open(path, encoding="utf-8"))
ids = {item.get("record_id") for item in payload.get("records", [])}
if record_id not in ids:
    raise SystemExit(f"PVK record {record_id} did not persist across restart")
PY_PERSIST

curl --fail --silent --show-error \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  "${base_url}/v1/audit?limit=500" > "${evidence_dir}/audit.after-restart.PRIVATE.json"
chmod 0600 "${evidence_dir}/audit.after-restart.PRIVATE.json"

python3 - "${evidence_dir}/audit.after-restart.PRIVATE.json" <<'PY_AUDIT'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
events = {item.get("event") for item in payload.get("records", [])}
required = {"physics_record_appended", "physics_claim_linted", "service_started"}
missing = sorted(required - events)
if missing:
    raise SystemExit(f"required audit events missing: {missing}")
PY_AUDIT

docker compose -p "$project_name" ps > "${evidence_dir}/compose.ps.txt"

# RESULT is written before SHA256SUMS so the final acceptance statement is itself hash-bound.
cat > "${evidence_dir}/RESULT.txt" <<EOF
ACTUAL_HOST_PVK_SHADOW_ACCEPTANCE=PASS
branch=${current_branch}
commit=${git_head}
shadow_port=${shadow_port}
relay_admin_boundary=PASS
pvk_record_append=PASS
pvk_claims_linter=PASS
pvk_restart_persistence=PASS
pvk_audit_presence=PASS
scientific_validation_claim=NOT_ESTABLISHED_BY_THIS_TEST
EOF

# Hash all evidence except the checksum file itself. This includes RESULT.txt.
(
  cd "$evidence_dir"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)

echo "PASS: actual-host PVK shadow acceptance evidence: ${evidence_dir}"

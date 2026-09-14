#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env is required for the QCRYPTO ECHO bridge exercise." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a
: "${SARA_ADMIN_TOKEN:?SARA_ADMIN_TOKEN is required}"

project="ws-qcrypto-echo-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-0}"
project="${project//[^A-Za-z0-9_.-]/-}"
sara_port="${QCRYPTO_SARA_HOST_PORT:-19531}"
echo_port="${QCRYPTO_ECHO_HOST_PORT:-19551}"
sara_url="http://127.0.0.1:${sara_port}"
echo_url="http://127.0.0.1:${echo_port}"
service_uid="${QCRYPTO_CONTAINER_UID:-10001}"

secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/qcrypto-echo-bridge.XXXXXX")"
token_file="${secret_dir}/echo-ingest-token"
checkpoint_key_file="${secret_dir}/echo-checkpoint-ed25519-private.pem"
evidence_file="${QCRYPTO_ECHO_BRIDGE_EVIDENCE_FILE:-${secret_dir}/qcrypto-echo-bridge-evidence.json}"

compose=(
  docker compose
  -p "$project"
  -f compose.yaml
  -f compose.qcrypto-echo.yaml
  --profile echo
)

cleanup() {
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$secret_dir" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Use a fresh isolated project so retained events from another validation run
# cannot make exact four-record reconciliation appear successful or fail spuriously.
"${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true

echo_token="$(openssl rand -hex 32)"
printf '%s\n' "$echo_token" > "$token_file"
openssl genpkey -algorithm Ed25519 -out "$checkpoint_key_file" >/dev/null 2>&1
chmod 0600 "$token_file" "$checkpoint_key_file"
if [[ "$(id -u)" -eq 0 ]]; then
  chown "${service_uid}:${service_uid}" "$token_file" "$checkpoint_key_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${service_uid}:${service_uid}" "$token_file" "$checkpoint_key_file"
else
  echo "ERROR: cannot set bridge secret ownership to UID ${service_uid}." >&2
  exit 1
fi

export SARA_HOST_PORT="$sara_port"
export ECHO_HOST_PORT="$echo_port"
export ECHO_INGEST_TOKEN_HOST_PATH="$token_file"
export ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH="$checkpoint_key_file"
export ECHO_CHECKPOINT_KEY_ID="ECHO-QCRYPTO-BRIDGE-${GITHUB_SHA:-LOCAL}"

# Render first: this catches network, mount, profile, and interpolation errors
# before any service starts.
"${compose[@]}" config --quiet
"${compose[@]}" up -d --build sara echo

wait_url() {
  local url="$1"
  for attempt in $(seq 1 40); do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      return 0
    fi
    echo "Readiness attempt ${attempt}/40: ${url}"
    sleep 2
  done
  return 1
}
wait_url "${sara_url}/readyz" || {
  "${compose[@]}" logs --no-color --tail=120 sara >&2 || true
  exit 1
}
wait_url "${echo_url}/readyz" || {
  "${compose[@]}" logs --no-color --tail=120 echo >&2 || true
  exit 1
}

# Prove the opt-in topology is narrow: SARA joins the ECHO private network for
# HTTP evidence transport, but does not receive ECHO data/checkpoint-key mounts.
sara_container="$("${compose[@]}" ps -q sara)"
echo_container="$("${compose[@]}" ps -q echo)"
docker inspect "$sara_container" > "${secret_dir}/sara-inspect.json"
docker inspect "$echo_container" > "${secret_dir}/echo-inspect.json"
python3 - "${secret_dir}/sara-inspect.json" "${secret_dir}/echo-inspect.json" <<'PY'
import json, sys
from pathlib import Path
sara=json.loads(Path(sys.argv[1]).read_text())[0]
echo=json.loads(Path(sys.argv[2]).read_text())[0]
sara_mounts={m['Destination'] for m in sara.get('Mounts', [])}
echo_mounts={m['Destination'] for m in echo.get('Mounts', [])}
sara_networks=set((sara.get('NetworkSettings',{}).get('Networks') or {}).keys())
echo_networks=set((echo.get('NetworkSettings',{}).get('Networks') or {}).keys())
assert sara_networks & echo_networks, (sara_networks, echo_networks)
assert '/run/worldshepherd-sara/echo-forward-token' in sara_mounts
assert '/run/worldshepherd-echo/checkpoint-ed25519-private.pem' not in sara_mounts
assert '/var/lib/echo' not in sara_mounts
assert '/run/worldshepherd-echo/checkpoint-ed25519-private.pem' in echo_mounts
assert '/var/lib/echo' in echo_mounts
PY

admin_header=( -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" -H 'Content-Type: application/json' )
echo_header=( -H "Authorization: Bearer ${echo_token}" -H 'Content-Type: application/json' )

cat > "${secret_dir}/projection.json" <<'JSON'
{
  "schema": "WS-QCRYPTO-CONTROL-DECISION-V1",
  "asset_id": "QCRYPTO-BRIDGE-CI-ASSET",
  "echo_state": "ECHO_PROVENANCE_ACCEPTED",
  "prime_state": "PRIME_RECOMMENDS_PRIORITY_MIGRATION_PLAN",
  "sara_state": "SARA_PLAN_AUTHORIZED",
  "overwatch_state": "OVERWATCH_TRACK_AUTHORIZED_PLAN",
  "priority": "P0_MIGRATION_PRIORITY",
  "human_approval_required": true,
  "migration_executed": false,
  "execution_authority": false,
  "live_value_authorized": false,
  "federal_compliance_established": false,
  "ws_cae_conformance_established": false,
  "claim_boundary": "INTERNAL_PQC_CONTROL_PLANE_NOT_FEDERAL_COMPLIANCE",
  "correlation_id": "QCRYPTO-ECHO-BRIDGE-CI"
}
JSON

curl --fail --silent --show-error -X POST "${sara_url}/admin/qcrypto/audit" \
  "${admin_header[@]}" --data @"${secret_dir}/projection.json" \
  > "${secret_dir}/submit.json"

readarray -t identity < <(python3 - "${secret_dir}/submit.json" <<'PY'
import json, re, sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text())
assert body['accepted'] is True
assert body['provenance_delivery']=='DELIVERED'
assert body['decision_digest'].startswith('sha256:') and len(body['decision_digest'])==71
assert re.fullmatch(r'QCRYPTO-AUDIT-[0-9a-f]{32}', body['audit_instance_id'])
assert len(body['event_ids'])==4 and len(set(body['event_ids']))==4
assert body['migration_executed'] is False
assert body['execution_authority'] is False
assert body['live_value_authorized'] is False
print(body['decision_digest'])
print(body['audit_instance_id'])
PY
)
digest="${identity[0]}"
instance="${identity[1]}"

sync_url="${sara_url}/admin/qcrypto/audit/echo-sync?decision_digest=${digest}&audit_instance_id=${instance}"
curl --fail --silent --show-error -X POST "$sync_url" -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  > "${secret_dir}/sync-first.json"
curl --fail --silent --show-error -X POST "$sync_url" -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  > "${secret_dir}/sync-replay.json"\n
python3 - "${secret_dir}/sync-first.json" "${secret_dir}/sync-replay.json" "$instance" <<'PY'
import json, sys
from pathlib import Path
first=json.loads(Path(sys.argv[1]).read_text()); replay=json.loads(Path(sys.argv[2]).read_text())
instance=sys.argv[3]
for body in (first,replay):
    assert body['verification']['verdict']=='INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN'
    assert body['verification']['audit_instance_id']==instance
    assert body['verification']['complete'] is True
    assert body['verification']['consistent'] is True
    assert body['sync']['execution_authority'] is False
    assert body['sync']['live_value_authorized'] is False
    assert body['sync']['reconciliation']['counts']=={
        'MATCHED':4,'SARA_ONLY':0,'ECHO_ONLY':0,'PAYLOAD_MISMATCH':0
    }
assert first['sync']['stored_count']==4 and first['sync']['deduplicated_count']==0
assert replay['sync']['stored_count']==0 and replay['sync']['deduplicated_count']==4
assert first['sync']['event_ids']==replay['sync']['event_ids']
PY

curl --fail --silent --show-error \
  "${sara_url}/admin/qcrypto/audit/verify?decision_digest=${digest}&audit_instance_id=${instance}" \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" > "${secret_dir}/verify.json"

curl --fail --silent --show-error "${echo_url}/v1/status" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/echo-status.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/checkpoint" \
  "${echo_header[@]}" > "${secret_dir}/checkpoint.json"

python3 - "${secret_dir}/verify.json" "${secret_dir}/echo-status.json" \
  "${secret_dir}/checkpoint.json" "${secret_dir}/sync-first.json" \
  "${secret_dir}/sync-replay.json" "$digest" "$instance" "$evidence_file" <<'PY'
import json, sys
from pathlib import Path
verify=json.loads(Path(sys.argv[1]).read_text())
status=json.loads(Path(sys.argv[2]).read_text())
checkpoint=json.loads(Path(sys.argv[3]).read_text())
first=json.loads(Path(sys.argv[4]).read_text())
replay=json.loads(Path(sys.argv[5]).read_text())
digest=sys.argv[6]; instance=sys.argv[7]; out=Path(sys.argv[8])
assert verify['verification']['verdict']=='INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN'
assert verify['verification']['logical_event_count']==4
assert verify['verification']['audit_instance_id']==instance
assert status['ok'] is True and status['stored_events']==4
assert checkpoint['manifest']['event_count']==4
assert checkpoint['manifest']['algorithm']=='Ed25519'
summary={
    'schema':'WS-QCRYPTO-ECHO-DEPLOYED-BRIDGE-EVIDENCE-V1',
    'status':'PASS',
    'decision_digest':digest,
    'audit_instance_id':instance,
    'first_sync':{
        'stored_count':first['sync']['stored_count'],
        'deduplicated_count':first['sync']['deduplicated_count'],
        'reconciliation_counts':first['sync']['reconciliation']['counts'],
    },
    'replay_sync':{
        'stored_count':replay['sync']['stored_count'],
        'deduplicated_count':replay['sync']['deduplicated_count'],
        'reconciliation_counts':replay['sync']['reconciliation']['counts'],
    },
    'echo_stored_events':status['stored_events'],
    'checkpoint_algorithm':checkpoint['manifest']['algorithm'],
    'checkpoint_event_count':checkpoint['manifest']['event_count'],
    'execution_authority':False,
    'live_value_authorized':False,
    'claims_boundary':(
        'Internal containerized software evidence only. This exercise demonstrates bounded SARA-to-ECHO '
        'evidence synchronization, exact four-record reconciliation, retry deduplication, instance-scoped '
        'identity, and classical Ed25519 checkpoint creation. It does not establish post-quantum checkpoint '
        'security, migration execution, live-value authorization, external attestation, Federal compliance, '
        'WS-CAE conformance, or production deployment.'
    ),
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY

echo "QCRYPTO SARA-to-ECHO deployed bridge: PASS (${evidence_file})"

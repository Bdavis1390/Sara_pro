#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing; run normal deployment setup first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a
: "${SARA_ADMIN_TOKEN:?SARA_ADMIN_TOKEN is required}"

sara_port="${SARA_HOST_PORT:-9530}"
sara_url="${SARA_BASE_URL:-http://127.0.0.1:${sara_port}}"
echo_port="${ECHO_HOST_PORT:-19550}"
echo_url="http://127.0.0.1:${echo_port}"
echo_uid="${ECHO_CONTAINER_UID:-10001}"
short_sha="${GITHUB_SHA:-LOCAL}"
short_sha="${short_sha:0:12}"
prime_id="PRIME-ECHO-CI-${GITHUB_RUN_ID:-LOCAL}-${GITHUB_RUN_ATTEMPT:-0}-${short_sha}"
prime_id_2="${prime_id}-B"
evidence_file="${ECHO_PERSISTENCE_EVIDENCE_FILE:-echo-persistence-integration.json}"

secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/echo-ci.XXXXXX")"
token_file="${secret_dir}/echo-ingest-token"
checkpoint_key_file="${secret_dir}/echo-checkpoint-ed25519-private.pem"
cleanup() {
  docker compose --profile echo rm -sf echo >/dev/null 2>&1 || true
  rm -rf "$secret_dir" 2>/dev/null || true
}
trap cleanup EXIT

echo_token="$(openssl rand -hex 32)"
printf '%s\n' "$echo_token" > "$token_file"
openssl genpkey -algorithm Ed25519 -out "$checkpoint_key_file" >/dev/null 2>&1
chmod 600 "$token_file" "$checkpoint_key_file"
checkpoint_fingerprint="$(python3 - "$checkpoint_key_file" <<'PY'
import hashlib, sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
key=serialization.load_pem_private_key(Path(sys.argv[1]).read_bytes(), password=None)
raw=key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
print(hashlib.sha256(raw).hexdigest())
PY
)"

if [[ "$(id -u)" -eq 0 ]]; then
  chown "${echo_uid}:${echo_uid}" "$token_file" "$checkpoint_key_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${echo_uid}:${echo_uid}" "$token_file" "$checkpoint_key_file"
else
  echo "ERROR: cannot set ECHO secret ownership to UID ${echo_uid}." >&2
  exit 1
fi

export ECHO_INGEST_TOKEN_HOST_PATH="$token_file"
export ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH="$checkpoint_key_file"
export ECHO_CHECKPOINT_KEY_ID="ECHO-CHECKPOINT-CI-${short_sha}"
export ECHO_HOST_PORT="$echo_port"

docker compose --profile echo up -d --build echo

wait_echo() {
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error "${echo_url}/readyz" > "${secret_dir}/echo-ready.json"; then
      return 0
    fi
    echo "ECHO readiness attempt ${attempt}/30..."
    sleep 2
  done
  return 1
}
wait_echo || {
  echo "ERROR: ECHO did not become ready." >&2
  docker compose --profile echo logs --no-color --tail=100 echo >&2 || true
  exit 1
}

echo_container="$(docker compose --profile echo ps -q echo)"
sara_container="$(docker compose ps -q sara)"
[[ -n "$echo_container" && -n "$sara_container" ]] || {
  echo "ERROR: SARA or ECHO container not found." >&2
  exit 1
}
docker inspect "$echo_container" > "${secret_dir}/echo-inspect.json"
docker inspect "$sara_container" > "${secret_dir}/sara-inspect.json"
python3 - "${secret_dir}/echo-inspect.json" "${secret_dir}/sara-inspect.json" <<'PY'
import json, sys
from pathlib import Path
echo=json.loads(Path(sys.argv[1]).read_text())[0]
sara=json.loads(Path(sys.argv[2]).read_text())[0]
echo_env=set(echo['Config'].get('Env') or [])
sara_env=set(sara['Config'].get('Env') or [])
for item in ('SARA_ADMIN_TOKEN=', 'SARA_RELAY_TOKEN=', 'PRIME_SENTINEL_SERVICE_TOKEN='):
    assert item in echo_env
assert 'ECHO_INGEST_TOKEN_FILE=/run/worldshepherd-echo/ingest-token' in echo_env
assert 'ECHO_CHECKPOINT_PRIVATE_KEY_FILE=/run/worldshepherd-echo/checkpoint-ed25519-private.pem' in echo_env
assert 'ECHO_INGEST_TOKEN_FILE=' in sara_env
assert 'ECHO_DATA_DIR=' in sara_env
assert 'ECHO_CHECKPOINT_PRIVATE_KEY_FILE=' in sara_env
assert 'ECHO_CHECKPOINT_KEY_ID=' in sara_env
echo_mounts={item['Destination'] for item in echo.get('Mounts', [])}
sara_mounts={item['Destination'] for item in sara.get('Mounts', [])}
for target in ('/run/worldshepherd-echo/ingest-token','/run/worldshepherd-echo/checkpoint-ed25519-private.pem','/var/lib/echo'):
    assert target in echo_mounts
    assert target not in sara_mounts
assert '/var/lib/sara' not in echo_mounts
echo_networks=set((echo.get('NetworkSettings',{}).get('Networks') or {}).keys())
sara_networks=set((sara.get('NetworkSettings',{}).get('Networks') or {}).keys())
assert echo_networks and sara_networks and echo_networks.isdisjoint(sara_networks)
PY

admin_header=( -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" -H 'Content-Type: application/json' )
echo_header=( -H "Authorization: Bearer ${echo_token}" -H 'Content-Type: application/json' )

create_source_record() {
  local prime="$1" passport_out="$2" event_out="$3" record_out="$4"
  curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime}/passport" \
    "${admin_header[@]}" \
    --data "{\"hardware_revision\":\"HW-ECHO-CI\",\"software_revision\":\"SW-ECHO-CI\",\"evidence_refs\":[\"ECHO:CI:CHECKPOINT:SOURCE\"]}" \
    > "$passport_out"
  python3 - "$passport_out" "$event_out" <<'PY'
import json, sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text())
ids=body['provenance_event_ids']
assert len(ids)==1 and body['provenance_delivery']=='DELIVERED'
Path(sys.argv[2]).write_text(ids[0], encoding='utf-8')
PY
  local eid
  eid="$(cat "$event_out")"
  curl --fail --silent --show-error "${sara_url}/v1/audit?limit=500" \
    -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" > "${secret_dir}/audit.json"
  python3 - "${secret_dir}/audit.json" "$eid" "$record_out" <<'PY'
import json, sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text()); eid=sys.argv[2]
matches=[r for r in body['records'] if isinstance(r,dict) and isinstance(r.get('payload'),dict) and r['payload'].get('_outbox_event_id')==eid]
assert matches
record=matches[-1]
assert record['payload']['_delivery_semantics']=='AT_LEAST_ONCE'
Path(sys.argv[3]).write_text(json.dumps(record,sort_keys=True)+'\n',encoding='utf-8')
PY
}

create_source_record "$prime_id" "${secret_dir}/passport1.json" "${secret_dir}/event1.txt" "${secret_dir}/source1.json"
event_id="$(cat "${secret_dir}/event1.txt")"
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" \
  --data @"${secret_dir}/source1.json" > "${secret_dir}/ingest-first.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" \
  --data @"${secret_dir}/source1.json" > "${secret_dir}/ingest-replay.json"
python3 - "${secret_dir}/ingest-first.json" "${secret_dir}/ingest-replay.json" "$event_id" <<'PY'
import json,sys
from pathlib import Path
first=json.loads(Path(sys.argv[1]).read_text()); replay=json.loads(Path(sys.argv[2]).read_text())
assert first['outcome']=='STORED' and replay['outcome']=='DEDUPLICATED'
assert first['event_id']==replay['event_id']==sys.argv[3]
assert first['semantic_sha256']==replay['semantic_sha256'] and replay['delivery_count']==2
PY

curl --fail --silent --show-error -X POST "${echo_url}/v1/checkpoint" "${echo_header[@]}" \
  > "${secret_dir}/checkpoint1.json"
python3 - "${secret_dir}/checkpoint1.json" <<'PY'
import json,sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text())
assert body['manifest']['sequence']==1 and body['manifest']['event_count']>=1
assert body['manifest']['previous_checkpoint_sha256'] is None
PY

docker compose --profile echo restart echo >/dev/null
wait_echo || { echo "ERROR: ECHO failed readiness after checkpoint restart." >&2; exit 1; }
curl --fail --silent --show-error "${echo_url}/v1/checkpoint/1" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/checkpoint1-after-restart.json"
python3 - "${secret_dir}/checkpoint1.json" "${secret_dir}/checkpoint1-after-restart.json" <<'PY'
import json,sys
from pathlib import Path
assert json.loads(Path(sys.argv[1]).read_text()) == json.loads(Path(sys.argv[2]).read_text())
PY

python3 - "${secret_dir}/source1.json" "${secret_dir}/replay-after-restart.json" <<'PY'
import json,sys
from datetime import datetime,timezone
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text()); record['timestamp']=datetime.now(timezone.utc).isoformat()
Path(sys.argv[2]).write_text(json.dumps(record,sort_keys=True)+'\n')
PY
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" \
  --data @"${secret_dir}/replay-after-restart.json" > "${secret_dir}/ingest-after-restart.json"
python3 - "${secret_dir}/ingest-after-restart.json" <<'PY'
import json,sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text())
assert body['outcome']=='DEDUPLICATED' and body['delivery_count']==3
PY

create_source_record "$prime_id_2" "${secret_dir}/passport2.json" "${secret_dir}/event2.txt" "${secret_dir}/source2.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" \
  --data @"${secret_dir}/source2.json" > "${secret_dir}/ingest-second.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/checkpoint" "${echo_header[@]}" \
  > "${secret_dir}/checkpoint2.json"

curl --fail --silent --show-error "${echo_url}/v1/checkpoint/public-key" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/checkpoint-public-key.json"
python3 - "${secret_dir}/checkpoint-public-key.json" "$checkpoint_fingerprint" \
  "${secret_dir}/checkpoint1.json" "${secret_dir}/checkpoint2.json" <<'PY'
import json,sys
from pathlib import Path
pub=json.loads(Path(sys.argv[1]).read_text()); fp=sys.argv[2]
one=json.loads(Path(sys.argv[3]).read_text()); two=json.loads(Path(sys.argv[4]).read_text())
assert pub['fingerprint_sha256']==fp
assert two['manifest']['sequence']==2
assert two['manifest']['previous_checkpoint_sha256']==one['checkpoint_sha256']
assert two['manifest']['event_count'] >= 2
PY

ws-echo-checkpoint-verify --expected-fingerprint "$checkpoint_fingerprint" \
  --output "${secret_dir}/verification.json" \
  "${secret_dir}/checkpoint1.json" "${secret_dir}/checkpoint2.json" >/dev/null

python3 - "${secret_dir}/checkpoint2.json" "$secret_dir" <<'PY'
import copy,json,sys
from pathlib import Path
source=json.loads(Path(sys.argv[1]).read_text()); root=Path(sys.argv[2])
variants={}
a=copy.deepcopy(source); a['manifest']['events']=a['manifest']['events'][:-1]; a['manifest']['event_count']=len(a['manifest']['events']); variants['deleted']=a
a=copy.deepcopy(source); a['manifest']['events'].reverse(); variants['reordered']=a
a=copy.deepcopy(source); a['manifest']['events'][0]['semantic_sha256']='0'*64; variants['substituted']=a
a=copy.deepcopy(source); a['signature_b64url']='A'*86; variants['signature']=a
a=copy.deepcopy(source); a['manifest']['previous_checkpoint_sha256']='0'*64; variants['predecessor']=a
a=copy.deepcopy(source); a['public_key']['fingerprint_sha256']='0'*64; variants['key']=a
for name,value in variants.items():
    (root/f'tamper-{name}.json').write_text(json.dumps(value,sort_keys=True)+'\n')
PY
for mutation in deleted reordered substituted signature predecessor key; do
  if ws-echo-checkpoint-verify --expected-fingerprint "$checkpoint_fingerprint" \
    "${secret_dir}/checkpoint1.json" "${secret_dir}/tamper-${mutation}.json" >/dev/null 2>&1; then
    echo "ERROR: tampered checkpoint unexpectedly verified: ${mutation}" >&2
    exit 1
  fi
done

curl --fail --silent --show-error "${echo_url}/v1/event/${event_id}" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/stored.json"
python3 - "${secret_dir}/source1.json" "${secret_dir}/reconcile-request.json" <<'PY'
import json,sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
Path(sys.argv[2]).write_text(json.dumps({'records':[record]},separators=(',',':'))+'\n')
PY
curl --fail --silent --show-error -X POST "${echo_url}/v1/reconcile" "${echo_header[@]}" \
  --data @"${secret_dir}/reconcile-request.json" > "${secret_dir}/reconcile.json"

python3 - "${secret_dir}/source1.json" "${secret_dir}/conflict.json" <<'PY'
import json,sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
record['payload']['evidence_refs']=['MUTATED-CONFLICT-CHECK']
Path(sys.argv[2]).write_text(json.dumps(record,sort_keys=True)+'\n')
PY
conflict_status="$(curl --silent --output "${secret_dir}/conflict-response.json" --write-out '%{http_code}' \
  -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" --data @"${secret_dir}/conflict.json")"
[[ "$conflict_status" == "409" ]] || {
  echo "ERROR: ECHO semantic conflict was not rejected; HTTP ${conflict_status}." >&2
  exit 1
}

curl --fail --silent --show-error "${echo_url}/v1/status" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/status.json"
python3 - "${secret_dir}/stored.json" "${secret_dir}/status.json" \
  "${secret_dir}/reconcile.json" "${secret_dir}/verification.json" \
  "$event_id" "$prime_id" "$evidence_file" <<'PY'
import json,sys
from pathlib import Path
stored=json.loads(Path(sys.argv[1]).read_text()); status=json.loads(Path(sys.argv[2]).read_text())
reconcile=json.loads(Path(sys.argv[3]).read_text()); verification=json.loads(Path(sys.argv[4]).read_text())
out=Path(sys.argv[7])
assert stored['delivery_count']==3
assert status['ok'] is True and status['rejected_conflicts'] >= 1
assert status['checkpoints']['ok'] is True and status['checkpoints']['checkpoint_count']==2
expected_counts={'MATCHED':1,'ECHO_ONLY':1}
assert reconcile['scope']=='PROVIDED_SARA_AUDIT_WINDOW' and reconcile['counts']==expected_counts, reconcile
assert verification['status']=='PASS' and verification['checkpoint_count']==2
summary={
  'schema':'WS-ECHO-CHECKPOINT-INTEGRATION-V1',
  'status':'PASS',
  'prime_id':sys.argv[6],
  'event_id':sys.argv[5],
  'semantic_sha256':stored['semantic_sha256'],
  'delivery_count_after_restart':stored['delivery_count'],
  'checkpoint_count':verification['checkpoint_count'],
  'last_checkpoint_sha256':verification['last_checkpoint_sha256'],
  'expected_key_fingerprint_sha256':verification['expected_key_fingerprint_sha256'],
  'tamper_cases_rejected':['deleted','reordered','substituted','signature','predecessor','key'],
  'semantic_conflict_rejected_http_status':409,
  'reconciliation_scope':reconcile['scope'],
  'reconciliation_counts':reconcile['counts'],
  'separation_checks':{
    'echo_has_no_sara_bearer_credentials':True,
    'echo_has_no_sara_data_mount':True,
    'sara_has_no_echo_ingest_or_checkpoint_secret_or_data_mount':True,
    'sara_and_echo_share_no_docker_network':True,
  },
  'claims_boundary':(
    'Internal reference software evidence only. Signed ECHO checkpoint creation, restart persistence, '
    'pinned-key independent verification, predecessor chaining, and tested tamper rejection are demonstrated. '
    'Immutable/WORM retention, external anchoring, privileged rollback resistance, third-party attestation, '
    'exactly-once transport, certification, and physical PRIME qualification are not established.'
  ),
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
PY

echo "ECHO persistence/checkpoint integration: PASS (${evidence_file})"

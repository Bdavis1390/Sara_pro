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
evidence_file="${ECHO_PERSISTENCE_EVIDENCE_FILE:-echo-persistence-integration.json}"

secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/echo-ci.XXXXXX")"
token_file="${secret_dir}/echo-ingest-token"
cleanup() {
  docker compose --profile echo rm -sf echo >/dev/null 2>&1 || true
  rm -rf "$secret_dir" 2>/dev/null || true
}
trap cleanup EXIT

echo_token="$(openssl rand -hex 32)"
printf '%s\n' "$echo_token" > "$token_file"
chmod 600 "$token_file"
if [[ "$(id -u)" -eq 0 ]]; then
  chown "${echo_uid}:${echo_uid}" "$token_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${echo_uid}:${echo_uid}" "$token_file"
else
  echo "ERROR: cannot set ECHO token ownership to UID ${echo_uid}." >&2
  exit 1
fi

export ECHO_INGEST_TOKEN_HOST_PATH="$token_file"
export ECHO_HOST_PORT="$echo_port"

docker compose --profile echo up -d --build echo

ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "${echo_url}/readyz" > "${secret_dir}/echo-ready.json"; then
    ready=1
    break
  fi
  echo "ECHO readiness attempt ${attempt}/30..."
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "ERROR: ECHO did not become ready." >&2
  docker compose --profile echo logs --no-color --tail=100 echo >&2 || true
  exit 1
fi

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

echo = json.loads(Path(sys.argv[1]).read_text())[0]
sara = json.loads(Path(sys.argv[2]).read_text())[0]
echo_env = set(echo['Config'].get('Env') or [])
sara_env = set(sara['Config'].get('Env') or [])
assert 'SARA_ADMIN_TOKEN=' in echo_env
assert 'SARA_RELAY_TOKEN=' in echo_env
assert 'PRIME_SENTINEL_SERVICE_TOKEN=' in echo_env
assert 'ECHO_INGEST_TOKEN_FILE=/run/worldshepherd-echo/ingest-token' in echo_env
assert 'ECHO_INGEST_TOKEN_FILE=' in sara_env
assert 'ECHO_DATA_DIR=' in sara_env

echo_mounts = {item['Destination'] for item in echo.get('Mounts', [])}
sara_mounts = {item['Destination'] for item in sara.get('Mounts', [])}
assert '/run/worldshepherd-echo/ingest-token' in echo_mounts
assert '/var/lib/echo' in echo_mounts
assert '/run/worldshepherd-echo/ingest-token' not in sara_mounts
assert '/var/lib/echo' not in sara_mounts
assert '/var/lib/sara' not in echo_mounts

echo_networks = set((echo.get('NetworkSettings', {}).get('Networks') or {}).keys())
sara_networks = set((sara.get('NetworkSettings', {}).get('Networks') or {}).keys())
assert echo_networks
assert sara_networks
assert echo_networks.isdisjoint(sara_networks)
PY

admin_header=( -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" -H 'Content-Type: application/json' )
curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime_id}/passport" \
  "${admin_header[@]}" \
  --data '{"hardware_revision":"HW-ECHO-CI","software_revision":"SW-ECHO-CI","evidence_refs":["ECHO:CI:PERSISTENCE:SOURCE"]}' \
  > "${secret_dir}/passport.json"

python3 - "${secret_dir}/passport.json" "${secret_dir}/event-id.txt" <<'PY'
import json, sys
from pathlib import Path
body = json.loads(Path(sys.argv[1]).read_text())
ids = body['provenance_event_ids']
assert len(ids) == 1
assert body['provenance_delivery'] == 'DELIVERED'
Path(sys.argv[2]).write_text(ids[0], encoding='utf-8')
PY
event_id="$(cat "${secret_dir}/event-id.txt")"

curl --fail --silent --show-error "${sara_url}/v1/audit?limit=500" \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  > "${secret_dir}/audit.json"
python3 - "${secret_dir}/audit.json" "$event_id" "${secret_dir}/source-record.json" <<'PY'
import json, sys
from pathlib import Path
body = json.loads(Path(sys.argv[1]).read_text())
event_id = sys.argv[2]
matches = [
    record for record in body['records']
    if isinstance(record, dict)
    and isinstance(record.get('payload'), dict)
    and record['payload'].get('_outbox_event_id') == event_id
]
assert len(matches) >= 1
record = matches[-1]
assert record['payload']['_delivery_semantics'] == 'AT_LEAST_ONCE'
Path(sys.argv[3]).write_text(json.dumps(record, sort_keys=True) + '\n', encoding='utf-8')
PY

echo_header=( -H "Authorization: Bearer ${echo_token}" -H 'Content-Type: application/json' )
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" \
  "${echo_header[@]}" --data @"${secret_dir}/source-record.json" \
  > "${secret_dir}/ingest-first.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" \
  "${echo_header[@]}" --data @"${secret_dir}/source-record.json" \
  > "${secret_dir}/ingest-replay.json"\n
python3 - "${secret_dir}/ingest-first.json" "${secret_dir}/ingest-replay.json" "$event_id" <<'PY'
import json, sys
from pathlib import Path
first=json.loads(Path(sys.argv[1]).read_text())
replay=json.loads(Path(sys.argv[2]).read_text())
assert first['outcome'] == 'STORED'
assert replay['outcome'] == 'DEDUPLICATED'
assert first['event_id'] == replay['event_id'] == sys.argv[3]
assert first['semantic_sha256'] == replay['semantic_sha256']
assert replay['delivery_count'] == 2
PY

docker compose --profile echo restart echo >/dev/null
ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "${echo_url}/readyz" > "${secret_dir}/echo-ready-after-restart.json"; then
    ready=1
    break
  fi
  sleep 2
done
[[ "$ready" -eq 1 ]] || { echo "ERROR: ECHO failed readiness after restart." >&2; exit 1; }

python3 - "${secret_dir}/source-record.json" "${secret_dir}/replay-after-restart.json" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
record['timestamp']=datetime.now(timezone.utc).isoformat()
Path(sys.argv[2]).write_text(json.dumps(record, sort_keys=True) + '\n')
PY
curl --fail --silent --show-error -X POST "${echo_url}/v1/ingest" \
  "${echo_header[@]}" --data @"${secret_dir}/replay-after-restart.json" \
  > "${secret_dir}/ingest-after-restart.json"

python3 - "${secret_dir}/ingest-after-restart.json" <<'PY'
import json, sys
from pathlib import Path
body=json.loads(Path(sys.argv[1]).read_text())
assert body['outcome'] == 'DEDUPLICATED'
assert body['delivery_count'] == 3
PY

curl --fail --silent --show-error "${echo_url}/v1/event/${event_id}" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/stored.json"
curl --fail --silent --show-error -X POST "${echo_url}/v1/reconcile" \
  "${echo_header[@]}" \
  --data "$(python3 - "${secret_dir}/source-record.json" <<'PY'
import json, sys
from pathlib import Path
print(json.dumps({'records':[json.loads(Path(sys.argv[1]).read_text())]}, separators=(',', ':')))
PY
)" > "${secret_dir}/reconcile.json"

python3 - "${secret_dir}/stored.json" "${secret_dir}/reconcile.json" <<'PY'
import json, sys
from pathlib import Path
stored=json.loads(Path(sys.argv[1]).read_text())
reconcile=json.loads(Path(sys.argv[2]).read_text())
assert stored['delivery_count'] == 3
assert reconcile['scope'] == 'PROVIDED_SARA_AUDIT_WINDOW'
assert reconcile['counts'] == {'MATCHED': 1}
PY

python3 - "${secret_dir}/source-record.json" "${secret_dir}/conflict.json" <<'PY'
import json, sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
record['payload']['evidence_refs']=['MUTATED-CONFLICT-CHECK']
Path(sys.argv[2]).write_text(json.dumps(record, sort_keys=True) + '\n')
PY
conflict_status="$(curl --silent --output "${secret_dir}/conflict-response.json" --write-out '%{http_code}' \
  -X POST "${echo_url}/v1/ingest" "${echo_header[@]}" --data @"${secret_dir}/conflict.json")"
[[ "$conflict_status" == "409" ]] || {
  echo "ERROR: ECHO semantic conflict was not rejected; HTTP ${conflict_status}." >&2
  exit 1
}

curl --fail --silent --show-error "${echo_url}/v1/status" \
  -H "Authorization: Bearer ${echo_token}" > "${secret_dir}/status.json"
python3 - \
  "${secret_dir}/source-record.json" \
  "${secret_dir}/stored.json" \
  "${secret_dir}/status.json" \
  "${secret_dir}/reconcile.json" \
  "$event_id" \
  "$prime_id" \
  "$evidence_file" <<'PY'
import hashlib, json, sys
from pathlib import Path
source=json.loads(Path(sys.argv[1]).read_text())
stored=json.loads(Path(sys.argv[2]).read_text())
status=json.loads(Path(sys.argv[3]).read_text())
reconcile=json.loads(Path(sys.argv[4]).read_text())
event_id=sys.argv[5]
prime_id=sys.argv[6]
out=Path(sys.argv[7])
assert status['ok'] is True
assert status['stored_events'] >= 1
assert status['rejected_conflicts'] >= 1
summary={
  'schema':'WS-ECHO-TWO-CONTAINER-INTEGRATION-V1',
  'status':'PASS',
  'prime_id':prime_id,
  'event_id':event_id,
  'semantic_sha256':stored['semantic_sha256'],
  'delivery_count_after_restart':stored['delivery_count'],
  'semantic_conflict_rejected_http_status':409,
  'reconciliation_scope':reconcile['scope'],
  'reconciliation_counts':reconcile['counts'],
  'source_record_sha256':hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
  'separation_checks':{
    'echo_has_no_sara_bearer_credentials':True,
    'echo_has_no_sara_data_mount':True,
    'sara_has_no_echo_secret_or_data_mount':True,
    'sara_and_echo_share_no_docker_network':True,
  },
  'claims_boundary':(
    'Internal reference software evidence only. Input transport remains AT_LEAST_ONCE; '
    'ECHO provides idempotent semantic storage by stable SARA event ID. Exactly-once '
    'transport, immutable/WORM storage, external attestation, certification, and physical '
    'PRIME qualification are not established.'
  ),
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n', encoding='utf-8')
PY

echo "ECHO persistence/dedup integration: PASS (${evidence_file})"

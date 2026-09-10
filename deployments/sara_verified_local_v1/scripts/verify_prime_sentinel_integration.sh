#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing; run the normal deployment setup first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${SARA_ADMIN_TOKEN:?SARA_ADMIN_TOKEN is required}"

sara_port="${SARA_HOST_PORT:-9530}"
sara_url="${SARA_BASE_URL:-http://127.0.0.1:${sara_port}}"
sentinel_port="${PRIME_SENTINEL_HOST_PORT:-19540}"
sentinel_url="http://127.0.0.1:${sentinel_port}"
sentinel_uid="${PRIME_SENTINEL_CONTAINER_UID:-10001}"
short_sha="${GITHUB_SHA:-LOCAL}"
short_sha="${short_sha:0:12}"
key_id="PS-CI-${short_sha}"
prime_id="PRIME-CI-${GITHUB_RUN_ID:-LOCAL}-${GITHUB_RUN_ATTEMPT:-0}-${short_sha}"
evidence_file="${PRIME_SENTINEL_EVIDENCE_FILE:-prime-sentinel-integration.json}"

secret_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/prime-sentinel-ci.XXXXXX")"
key_file="${secret_dir}/ed25519-private.pem"
token_file="${secret_dir}/service-token"
env_backup="${secret_dir}/sara.env.original"
cp .env "$env_backup"

cleanup() {
  cp "$env_backup" .env 2>/dev/null || true
  chmod 600 .env 2>/dev/null || true
  docker compose --profile prime-sentinel rm -sf prime-sentinel >/dev/null 2>&1 || true
  rm -rf "$secret_dir" 2>/dev/null || true
}
trap cleanup EXIT

openssl genpkey -algorithm ED25519 -out "$key_file"
service_token="$(openssl rand -hex 32)"
printf '%s\n' "$service_token" > "$token_file"
chmod 600 "$key_file" "$token_file"

if [[ "$(id -u)" -eq 0 ]]; then
  chown "${sentinel_uid}:${sentinel_uid}" "$key_file" "$token_file"
elif command -v sudo >/dev/null 2>&1; then
  sudo chown "${sentinel_uid}:${sentinel_uid}" "$key_file" "$token_file"
else
  echo "ERROR: cannot set PRIME SENTINEL secret-file ownership to UID ${sentinel_uid}." >&2
  exit 1
fi

export PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH="$key_file"
export PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH="$token_file"
export PRIME_SENTINEL_SIGNING_KEY_ID="$key_id"
export PRIME_SENTINEL_HOST_PORT="$sentinel_port"

docker compose --profile prime-sentinel up -d --build prime-sentinel

sentinel_ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "${sentinel_url}/readyz" > "${secret_dir}/sentinel-ready.json"; then
    sentinel_ready=1
    break
  fi
  echo "PRIME SENTINEL readiness attempt ${attempt}/30..."
  sleep 2
done
if [[ "$sentinel_ready" -ne 1 ]]; then
  echo "ERROR: PRIME SENTINEL did not become ready." >&2
  docker compose --profile prime-sentinel logs --no-color --tail=100 prime-sentinel >&2 || true
  exit 1
fi

curl --fail --silent --show-error "${sentinel_url}/v1/public-key" \
  > "${secret_dir}/public-key.json"

public_key="$(python3 - "${secret_dir}/public-key.json" "$key_id" <<'PY'
import json
import sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert record['schema'] == 'WS-PRIME-SENTINEL-PUBLIC-KEY-V1'
assert record['issuer'] == 'PRIME_SENTINEL'
assert record['algorithm'] == 'Ed25519'
assert record['key_id'] == sys.argv[2]
assert len(record['public_key_b64url']) >= 40
assert len(record['fingerprint_sha256']) == 64
print(record['public_key_b64url'])
PY
)"

sentinel_container="$(docker compose --profile prime-sentinel ps -q prime-sentinel)"
[[ -n "$sentinel_container" ]] || { echo "ERROR: PRIME SENTINEL container not found." >&2; exit 1; }
docker inspect "$sentinel_container" > "${secret_dir}/sentinel-inspect.json"
python3 - "${secret_dir}/sentinel-inspect.json" <<'PY'
import json
import sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))[0]
env = record['Config'].get('Env') or []
assert not any(item.startswith('SARA_ADMIN_TOKEN=') for item in env)
assert not any(item.startswith('SARA_RELAY_TOKEN=') for item in env)
assert not any(item.startswith('PRIME_SENTINEL_SERVICE_TOKEN=') for item in env)
assert any(item == 'PRIME_SENTINEL_SERVICE_TOKEN_FILE=/run/worldshepherd-prime-sentinel/service-token' for item in env)
mount_targets = {item['Destination'] for item in record.get('Mounts', [])}
assert '/run/worldshepherd-prime-sentinel/ed25519-private.pem' in mount_targets
assert '/run/worldshepherd-prime-sentinel/service-token' in mount_targets
PY

python3 - .env "$key_id" "$public_key" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
key_id = sys.argv[2]
public_key = sys.argv[3]
value = json.dumps({key_id: public_key}, separators=(',', ':'))
lines = path.read_text(encoding='utf-8').splitlines()
lines = [line for line in lines if not line.startswith('PRIME_SENTINEL_PUBLIC_KEYS_JSON=')]
lines.append("PRIME_SENTINEL_PUBLIC_KEYS_JSON='" + value + "'")
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
path.chmod(0o600)
PY

docker compose up -d --force-recreate sara

sara_ready=0
for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "${sara_url}/readyz" > "${secret_dir}/sara-ready.json"; then
    sara_ready=1
    break
  fi
  echo "SARA readiness after verifier-key injection ${attempt}/30..."
  sleep 2
done
if [[ "$sara_ready" -ne 1 ]]; then
  echo "ERROR: SARA did not become ready with PRIME SENTINEL public verification key." >&2
  docker compose logs --no-color --tail=100 sara >&2 || true
  exit 1
fi

sara_container="$(docker compose ps -q sara)"
[[ -n "$sara_container" ]] || { echo "ERROR: SARA container not found." >&2; exit 1; }
docker inspect "$sara_container" > "${secret_dir}/sara-inspect.json"
python3 - "${secret_dir}/sara-inspect.json" <<'PY'
import json
import sys
from pathlib import Path
record = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))[0]
env = record['Config'].get('Env') or []
assert 'PRIME_SENTINEL_PRIVATE_KEY_FILE=' in env
assert 'PRIME_SENTINEL_SERVICE_TOKEN_FILE=' in env
assert 'PRIME_SENTINEL_SERVICE_TOKEN=' in env
assert 'PRIME_SENTINEL_SIGNING_KEY_ID=' in env
mount_targets = {item['Destination'] for item in record.get('Mounts', [])}
assert '/run/worldshepherd-prime-sentinel/ed25519-private.pem' not in mount_targets
assert '/run/worldshepherd-prime-sentinel/service-token' not in mount_targets
PY

admin_header=( -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" -H 'Content-Type: application/json' )

curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime_id}/passport" \
  "${admin_header[@]}" \
  --data '{"hardware_revision":"HW-CI","software_revision":"SW-CI","evidence_refs":["ECHO:CI:PRIME-SENTINEL:BUILD"]}' \
  > "${secret_dir}/passport.json"

curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime_id}/mission-complete" \
  "${admin_header[@]}" \
  --data '{"environment":"HADAL","evidence_refs":["ECHO:CI:PRIME-SENTINEL:HADAL"]}' \
  > "${secret_dir}/mission.json"

python3 - "${secret_dir}/mission.json" <<'PY'
import json, sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
assert record['passport']['custody']['state'] == 'QUARANTINED_FOR_REQUALIFICATION'
PY

curl --fail --silent --show-error -X PATCH "${sara_url}/admin/prime/${prime_id}/requalification" \
  "${admin_header[@]}" \
  --data '{"completed_checks":["DECONTAMINATION_CLEANING","MECHANICAL_INSPECTION","CONNECTOR_INSULATION_CHECK","SEAL_TRIBOLOGY_CONDITION","BATTERY_HEALTH","STRUCTURAL_HEALTH_REVIEW","PACK_PROVENANCE","TARGET_ENVIRONMENT_ACCEPTANCE"],"evidence_refs":["ECHO:CI:PRIME-SENTINEL:REQUAL"]}' \
  > "${secret_dir}/requalification.json"

curl --fail --silent --show-error -X POST "${sentinel_url}/v1/requalification-release" \
  -H "Authorization: Bearer ${service_token}" \
  -H 'Content-Type: application/json' \
  --data "{\"prime_id\":\"${prime_id}\",\"target_environment\":\"SPACE\",\"lifetime_seconds\":300}" \
  > "${secret_dir}/issued.json"

python3 - "${secret_dir}/issued.json" "$key_id" "$prime_id" <<'PY'
import json, sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
assert record['schema'] == 'WS-PRIME-SENTINEL-ISSUE-RESPONSE-V1'
a=record['assertion']
assert a['issuer'] == 'PRIME_SENTINEL'
assert a['key_id'] == sys.argv[2]
assert a['prime_id'] == sys.argv[3]
assert a['action'] == 'REQUALIFICATION_RELEASE'
assert a['target_environment'] == 'SPACE'
assert len(a['nonce']) >= 16
assert len(a['signature_b64url']) >= 80
PY

python3 - "${secret_dir}/issued.json" "${secret_dir}/assertion.json" <<'PY'
import json, sys
from pathlib import Path
record=json.loads(Path(sys.argv[1]).read_text())
Path(sys.argv[2]).write_text(json.dumps(record['assertion'], separators=(',', ':')) + '\n')
PY

curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime_id}/requalification/authorize" \
  "${admin_header[@]}" \
  --data @"${secret_dir}/assertion.json" \
  > "${secret_dir}/authorized.json"

replay_status="$(curl --silent --output "${secret_dir}/replay.json" --write-out '%{http_code}' \
  -X POST "${sara_url}/admin/prime/${prime_id}/requalification/authorize" \
  "${admin_header[@]}" \
  --data @"${secret_dir}/assertion.json")"
if [[ "$replay_status" != "403" ]]; then
  echo "ERROR: PRIME SENTINEL assertion replay was not rejected; HTTP ${replay_status}." >&2
  exit 1
fi

curl --fail --silent --show-error -X POST "${sara_url}/admin/prime/${prime_id}/activate-pack" \
  "${admin_header[@]}" \
  --data '{"pack":{"pack_id":"SPACE-PACK-CI","target_environment":"SPACE","authenticated":true,"compatible_with_prime":true,"target_environment_qualification_valid":true},"evidence_refs":["ECHO:CI:PRIME-SENTINEL:PACK"]}' \
  > "${secret_dir}/activated.json"

curl --fail --silent --show-error "${sara_url}/admin/registry" \
  -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  > "${secret_dir}/registry.json"

python3 - \
  "${secret_dir}/public-key.json" \
  "${secret_dir}/issued.json" \
  "${secret_dir}/authorized.json" \
  "${secret_dir}/activated.json" \
  "${secret_dir}/registry.json" \
  "$prime_id" \
  "$evidence_file" <<'PY'
import json
import sys
from pathlib import Path
public = json.loads(Path(sys.argv[1]).read_text())
issued = json.loads(Path(sys.argv[2]).read_text())
authorized = json.loads(Path(sys.argv[3]).read_text())
activated = json.loads(Path(sys.argv[4]).read_text())
registry = json.loads(Path(sys.argv[5]).read_text())['registry']
prime_id = sys.argv[6]
out = Path(sys.argv[7])
assert authorized['passport']['custody']['requalification_release_authorization_id'] == issued['assertion']['authorization_id']
assert authorized['passport']['custody']['requalification_release_key_id'] == public['key_id']
assert activated['disposition'] == 'ACTIVATION_ALLOWED'
assert activated['passport']['custody']['state'] == 'READY'
auth_id = issued['assertion']['authorization_id']
auth_record = registry['PRIME_SENTINEL_AUTHORIZATIONS'][auth_id]
assert auth_record['status'] == 'CONSUMED'
summary = {
    'schema': 'WS-PRIME-SENTINEL-TWO-CONTAINER-INTEGRATION-V1',
    'status': 'PASS',
    'prime_id': prime_id,
    'signing_key_id': public['key_id'],
    'public_key_fingerprint_sha256': public['fingerprint_sha256'],
    'authorization_id': auth_id,
    'assertion_replay_rejected_http_status': 403,
    'activation_disposition': activated['disposition'],
    'authorization_registry_status': auth_record['status'],
    'separation_checks': {
        'sara_has_no_signer_secret_mounts': True,
        'sentinel_has_no_sara_bearer_credentials': True,
        'sentinel_bearer_not_in_container_environment': True,
    },
    'claims_boundary': (
        'Internal CI software evidence only; does not establish production/HSM key custody, '
        'external certification, partner validation, or physical PRIME qualification.'
    ),
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n', encoding='utf-8')
PY

echo "PRIME SENTINEL two-container integration: PASS (${evidence_file})"

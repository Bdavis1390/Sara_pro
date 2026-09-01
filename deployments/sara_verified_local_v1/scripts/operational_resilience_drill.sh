#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${OPS_RESILIENCE_EVIDENCE_DIR:-$ROOT/operational_resilience_evidence}"
SOURCE_SHA="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD)}"
HOST_PORT="${OPS_RESILIENCE_HOST_PORT:-19530}"
RUN_KEY="${GITHUB_RUN_ID:-local}-$$"
SAFE_KEY="${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
IMAGE="sara-ops-resilience:${SOURCE_SHA:0:12}"
DATA_VOLUME="sara_ops_resilience_${SAFE_KEY}"
CONTAINER="sara-ops-resilience-${SAFE_KEY}"
ADMIN_TOKEN="$(openssl rand -hex 32)"
RELAY_TOKEN="$(openssl rand -hex 32)"
INCIDENT_ID="WS-INC-${SAFE_KEY}"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.json "$OUT_DIR"/*.txt

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker volume rm "$DATA_VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

now_utc() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

wait_ready() {
  for _ in $(seq 1 60); do
    if curl --silent --show-error --fail "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  docker logs "$CONTAINER" >&2 || true
  return 1
}

echo '[ops] build exact tested image'
docker build \
  --build-arg SARA_BUILD_COMMIT="$SOURCE_SHA" \
  --build-arg SARA_RELEASE_ID="ops-resilience-${SOURCE_SHA}" \
  -t "$IMAGE" "$ROOT" >/dev/null

docker volume create "$DATA_VOLUME" >/dev/null
docker run --rm --user 0 -v "$DATA_VOLUME:/data" "$IMAGE" sh -c \
  "chown -R 10001:10001 /data && chmod 0700 /data && printf '%s\\n' '${INCIDENT_ID}' > /data/ops-resilience-marker.txt && chown 10001:10001 /data/ops-resilience-marker.txt"

start_runtime() {
  docker run -d \
    --name "$CONTAINER" \
    --read-only \
    --tmpfs /tmp:size=16m,mode=1777 \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    -p "127.0.0.1:${HOST_PORT}:9530" \
    -e SARA_RELAY_TOKEN="$RELAY_TOKEN" \
    -e SARA_ADMIN_TOKEN="$ADMIN_TOKEN" \
    -e SARA_BIND_HOST=0.0.0.0 \
    -e SARA_PORT=9530 \
    -e SARA_DATA_DIR=/var/lib/sara \
    -e SARA_MODE=operational-resilience-drill \
    -v "$DATA_VOLUME:/var/lib/sara" \
    "$IMAGE" >/dev/null
}

STARTED_UTC="$(now_utc)"
start_runtime
wait_ready
curl --silent --show-error --fail "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/pre-incident-health.json"

# Controlled incident injection: remove the runtime while preserving persistent state.
INJECTED_UTC="$(now_utc)"
docker rm -f "$CONTAINER" >/dev/null

DETECTED_UTC=''
for _ in $(seq 1 20); do
  if ! curl --silent --max-time 1 --fail "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null 2>&1; then
    DETECTED_UTC="$(now_utc)"
    break
  fi
  sleep 1
done
test -n "$DETECTED_UTC"
printf '%s\n' 'runtime_unavailable' > "$OUT_DIR/detected-condition.txt"

# Recovery action: recreate the runtime from the exact tested image and same retained state volume.
RECOVERY_STARTED_UTC="$(now_utc)"
start_runtime
wait_ready
RECOVERED_UTC="$(now_utc)"
curl --silent --show-error --fail "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/post-recovery-health.json"
curl --silent --show-error --fail "http://127.0.0.1:${HOST_PORT}/readyz" > "$OUT_DIR/post-recovery-readyz.json"

MARKER="$(docker run --rm -v "$DATA_VOLUME:/data:ro" "$IMAGE" cat /data/ops-resilience-marker.txt)"
test "$MARKER" = "$INCIDENT_ID"
printf '%s\n' "$MARKER" > "$OUT_DIR/preserved-state-marker.txt"

RUNTIME_IDENTITY="$(docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" | sed -n 's/^SARA_BUILD_COMMIT=//p')"
test "$RUNTIME_IDENTITY" = "$SOURCE_SHA"
printf '%s\n' "$RUNTIME_IDENTITY" > "$OUT_DIR/runtime-build-commit.txt"

export OUT_DIR SOURCE_SHA INCIDENT_ID STARTED_UTC INJECTED_UTC DETECTED_UTC RECOVERY_STARTED_UTC RECOVERED_UTC
python - <<'PY'
import datetime, hashlib, json, os, pathlib
from datetime import timezone
root = pathlib.Path(os.environ['OUT_DIR'])
health_before = json.loads((root/'pre-incident-health.json').read_text())
health_after = json.loads((root/'post-recovery-health.json').read_text())
ready_after = json.loads((root/'post-recovery-readyz.json').read_text())
marker = (root/'preserved-state-marker.txt').read_text().strip()
identity = (root/'runtime-build-commit.txt').read_text().strip()
parse = lambda s: datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
detected_s = max(0.0, (parse(os.environ['DETECTED_UTC']) - parse(os.environ['INJECTED_UTC'])).total_seconds())
recovery_s = max(0.0, (parse(os.environ['RECOVERED_UTC']) - parse(os.environ['RECOVERY_STARTED_UTC'])).total_seconds())
checks = {
    'pre_incident_health_ok': health_before.get('ok') is True,
    'incident_detection_recorded': (root/'detected-condition.txt').read_text().strip() == 'runtime_unavailable',
    'post_recovery_health_ok': health_after.get('ok') is True,
    'post_recovery_ready': ready_after.get('ok') is True and ready_after.get('status') == 'ready',
    'persistent_state_preserved': marker == os.environ['INCIDENT_ID'],
    'exact_build_identity_restored': identity == os.environ['SOURCE_SHA'],
    'detection_time_measured': detected_s >= 0,
    'recovery_time_measured': recovery_s >= 0,
}
files = ['pre-incident-health.json','detected-condition.txt','post-recovery-health.json','post-recovery-readyz.json','preserved-state-marker.txt','runtime-build-commit.txt']
record = {
    'schema': 'WS-SARA-OPERATIONAL-RESILIENCE-EVIDENCE-V1',
    'result': 'PASS' if all(checks.values()) else 'FAIL',
    'evidence_status': 'INTERNAL_CI_CONTROLLED_INCIDENT_DRILL',
    'incident_id': os.environ['INCIDENT_ID'],
    'source_build_commit': os.environ['SOURCE_SHA'],
    'timeline_utc': {
        'runtime_started': os.environ['STARTED_UTC'],
        'incident_injected': os.environ['INJECTED_UTC'],
        'incident_detected': os.environ['DETECTED_UTC'],
        'recovery_started': os.environ['RECOVERY_STARTED_UTC'],
        'recovery_completed': os.environ['RECOVERED_UTC'],
    },
    'measured_seconds': {'detection': detected_s, 'recovery': recovery_s},
    'severity': 'CONTROLLED_DRILL_RUNTIME_UNAVAILABLE',
    'containment': 'failed runtime removed; persistent volume retained',
    'recovery_action': 'recreate exact tested runtime and verify readiness/state/build identity',
    'retention_contract': {
        'artifact_class': 'operational-resilience-evidence',
        'required_objects': files,
        'index_digest_required': True,
        'production_retention_period': 'NOT ESTABLISHED BY THIS DRILL',
    },
    'checks': checks,
    'evidence_sha256': {name: 'sha256:' + hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
    'claims_boundary': (
        'This controlled CI drill demonstrates machine-detectable runtime loss, timestamped incident-state transitions, '
        'bounded recovery using retained state, readiness restoration, exact build identity, and evidence-retention metadata. '
        'It does not establish 24x7 staffing, production paging/on-call coverage, SIEM/SOC integration, customer escalation, '
        'legal/regulatory reporting, externally approved retention periods, production RTO/RPO, disaster recovery across '
        'failure domains, or SLA compliance.'
    ),
}
(root/'operational-resilience-evidence.json').write_text(json.dumps(record, sort_keys=True, indent=2)+'\n')
if record['result'] != 'PASS':
    raise SystemExit('OPERATIONAL_RESILIENCE: FAIL ' + json.dumps(checks, sort_keys=True))
print('OPERATIONAL_RESILIENCE: PASS')
PY

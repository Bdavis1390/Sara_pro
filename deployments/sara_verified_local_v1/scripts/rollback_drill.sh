#!/usr/bin/env bash
set -euo pipefail

CURRENT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE_DIR="${BASELINE_DIR:?BASELINE_DIR is required}"
BASELINE_SHA="${BASELINE_SHA:?BASELINE_SHA is required}"
CURRENT_SHA="${CURRENT_SHA:-${GITHUB_SHA:-$(git -C "$CURRENT_DIR" rev-parse HEAD)}}"
OUT_DIR="${ROLLBACK_EVIDENCE_DIR:-$CURRENT_DIR/rollback_evidence}"
HOST_PORT="${ROLLBACK_HOST_PORT:-19531}"
RUN_KEY="${GITHUB_RUN_ID:-local}-$$"
VOLUME="sara_rollback_${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
CURRENT_IMAGE="sara-rollback-current:${CURRENT_SHA:0:12}"
BASELINE_IMAGE="sara-rollback-baseline:${BASELINE_SHA:0:12}"
CURRENT_CONTAINER="sara-rollback-current-${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
BASELINE_CONTAINER="sara-rollback-baseline-${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
ADMIN_TOKEN="$(openssl rand -hex 32)"
RELAY_TOKEN="$(openssl rand -hex 32)"
MARKER="rollback-marker-${RUN_KEY}"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.json

cleanup() {
  docker rm -f "$CURRENT_CONTAINER" "$BASELINE_CONTAINER" >/dev/null 2>&1 || true
  docker volume rm "$VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

wait_ready() {
  local tries=60
  while (( tries > 0 )); do
    if curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    tries=$((tries - 1))
  done
  return 1
}

run_image() {
  local name="$1"
  local image="$2"
  docker run -d \
    --name "$name" \
    --read-only \
    --tmpfs /tmp:size=16m,mode=1777 \
    --security-opt no-new-privileges:true \
    --cap-drop ALL \
    -e SARA_RELAY_TOKEN="$RELAY_TOKEN" \
    -e SARA_ADMIN_TOKEN="$ADMIN_TOKEN" \
    -e SARA_BIND_HOST=0.0.0.0 \
    -e SARA_PORT=9530 \
    -e SARA_DATA_DIR=/var/lib/sara \
    -e SARA_MODE=rollback-drill \
    -p "127.0.0.1:${HOST_PORT}:9530" \
    -v "$VOLUME:/var/lib/sara" \
    "$image" >/dev/null
}

container_env_value() {
  local name="$1"
  local key="$2"
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$name" \
    | sed -n "s/^${key}=//p" \
    | head -n 1
}

echo "[rollback] building current image ${CURRENT_SHA}"
docker build \
  --build-arg SARA_BUILD_COMMIT="$CURRENT_SHA" \
  --build-arg SARA_RELEASE_ID="rollback-current-${CURRENT_SHA}" \
  -t "$CURRENT_IMAGE" "$CURRENT_DIR" >/dev/null

echo "[rollback] building frozen baseline image ${BASELINE_SHA}"
docker build \
  --build-arg SARA_BUILD_COMMIT="$BASELINE_SHA" \
  --build-arg SARA_RELEASE_ID="rollback-baseline-${BASELINE_SHA}" \
  -t "$BASELINE_IMAGE" "$BASELINE_DIR" >/dev/null

docker volume create "$VOLUME" >/dev/null

run_image "$CURRENT_CONTAINER" "$CURRENT_IMAGE"
wait_ready
curl -fsS "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/current-health.json"

python - "$MARKER" "$CURRENT_SHA" > "$OUT_DIR/marker-request.json" <<'PY'
import json, sys
marker, sha = sys.argv[1:]
print(json.dumps({"values":{"ROLLBACK_MARKER":{"marker":marker,"written_by_commit":sha}}}, sort_keys=True))
PY

curl -fsS -X PATCH \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary "@$OUT_DIR/marker-request.json" \
  "http://127.0.0.1:${HOST_PORT}/admin/registry" > "$OUT_DIR/current-registry-after-write.json"

CURRENT_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$CURRENT_CONTAINER")"
CURRENT_LABEL_REVISION="$(docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$CURRENT_CONTAINER")"
CURRENT_RUNTIME_COMMIT="$(container_env_value "$CURRENT_CONTAINER" SARA_BUILD_COMMIT)"

docker rm -f "$CURRENT_CONTAINER" >/dev/null

run_image "$BASELINE_CONTAINER" "$BASELINE_IMAGE"
wait_ready
curl -fsS "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/baseline-health.json"
curl -fsS \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "http://127.0.0.1:${HOST_PORT}/admin/registry" > "$OUT_DIR/baseline-registry.json"
curl -fsS \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "http://127.0.0.1:${HOST_PORT}/admin/selftest" > "$OUT_DIR/baseline-selftest.json"
curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" > "$OUT_DIR/baseline-readyz.json"

BASELINE_IMAGE_ID="$(docker inspect --format '{{.Image}}' "$BASELINE_CONTAINER")"
BASELINE_LABEL_REVISION="$(docker inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$BASELINE_CONTAINER")"
BASELINE_RUNTIME_COMMIT="$(container_env_value "$BASELINE_CONTAINER" SARA_BUILD_COMMIT)"

export OUT_DIR CURRENT_SHA BASELINE_SHA CURRENT_IMAGE_ID BASELINE_IMAGE_ID CURRENT_LABEL_REVISION BASELINE_LABEL_REVISION CURRENT_RUNTIME_COMMIT BASELINE_RUNTIME_COMMIT MARKER
python - <<'PY'
import datetime, hashlib, json, os, pathlib
root = pathlib.Path(os.environ['OUT_DIR'])

def load(name):
    return json.loads((root / name).read_text(encoding='utf-8'))

def sha(name):
    return 'sha256:' + hashlib.sha256((root / name).read_bytes()).hexdigest()

baseline_registry = load('baseline-registry.json')
selftest = load('baseline-selftest.json')
readyz = load('baseline-readyz.json')
marker_record = baseline_registry['registry']['ROLLBACK_MARKER']

checks = {
    'current_runtime_identity_matches_source': os.environ['CURRENT_RUNTIME_COMMIT'] == os.environ['CURRENT_SHA'],
    'baseline_runtime_identity_matches_target': os.environ['BASELINE_RUNTIME_COMMIT'] == os.environ['BASELINE_SHA'],
    'current_oci_revision_matches_source': os.environ['CURRENT_LABEL_REVISION'] == os.environ['CURRENT_SHA'],
    'baseline_oci_revision_matches_target': os.environ['BASELINE_LABEL_REVISION'] == os.environ['BASELINE_SHA'],
    'runtime_image_changed': os.environ['CURRENT_IMAGE_ID'] != os.environ['BASELINE_IMAGE_ID'],
    'persistent_marker_preserved': marker_record.get('marker') == os.environ['MARKER'],
    'persistent_marker_origin_preserved': marker_record.get('written_by_commit') == os.environ['CURRENT_SHA'],
    'baseline_ready': readyz.get('ok') is True and readyz.get('status') == 'ready',
    'baseline_selftest_passed': selftest.get('ok') is True,
}

record = {
    'schema': 'WS-SARA-ROLLBACK-DRILL-EVIDENCE-V1',
    'evidence_status': 'INTERNAL_CI_GENERATED_UNSIGNED',
    'executed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_build_commit': os.environ['CURRENT_SHA'],
    'rollback_target_commit': os.environ['BASELINE_SHA'],
    'source_runtime_build_commit': os.environ['CURRENT_RUNTIME_COMMIT'],
    'rollback_runtime_build_commit': os.environ['BASELINE_RUNTIME_COMMIT'],
    'source_container_image_id': os.environ['CURRENT_IMAGE_ID'],
    'rollback_container_image_id': os.environ['BASELINE_IMAGE_ID'],
    'source_oci_revision': os.environ['CURRENT_LABEL_REVISION'],
    'rollback_oci_revision': os.environ['BASELINE_LABEL_REVISION'],
    'checks': checks,
    'result': 'PASS' if all(checks.values()) else 'FAIL',
    'evidence_file_sha256': {
        name: sha(name) for name in (
            'current-health.json', 'current-registry-after-write.json',
            'baseline-health.json', 'baseline-registry.json',
            'baseline-selftest.json', 'baseline-readyz.json'
        )
    },
    'data_scope': 'synthetic rollback marker only',
    'claims_boundary': (
        'This evidence demonstrates a bounded CI rollback from the tested source build to the frozen internal baseline '
        'while preserving the exercised registry state on one Docker named volume. It does not establish production '
        'rollback approval, arbitrary schema downgrade compatibility, zero-downtime behavior, distributed rollback, '
        'external recovery validation, operational authority, certification, or field readiness.'
    ),
}
(root / 'rollback-drill.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n', encoding='utf-8')
if record['result'] != 'PASS':
    raise SystemExit('ROLLBACK_DRILL: FAIL ' + json.dumps(checks, sort_keys=True))
print('ROLLBACK_DRILL: PASS')
PY

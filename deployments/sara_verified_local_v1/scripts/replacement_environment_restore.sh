#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${REPLACEMENT_RECOVERY_DIR:-$ROOT/replacement_recovery_evidence}"
HOST_PORT="${REPLACEMENT_HOST_PORT:-19532}"
SOURCE_SHA="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD)}"
RUN_KEY="${GITHUB_RUN_ID:-local}-$$"
SAFE_KEY="${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
IMAGE="sara-replacement-restore:${SOURCE_SHA:0:12}"
SOURCE_VOLUME="sara_source_${SAFE_KEY}"
REPLACEMENT_VOLUME="sara_replacement_${SAFE_KEY}"
SOURCE_CONTAINER="sara-source-${SAFE_KEY}"
REPLACEMENT_CONTAINER="sara-replacement-${SAFE_KEY}"
ADMIN_TOKEN="$(openssl rand -hex 32)"
RELAY_TOKEN="$(openssl rand -hex 32)"
MARKER="replacement-restore-${SAFE_KEY}"
ARCHIVE="$OUT_DIR/source-backup.tar.gz"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.json "$ARCHIVE" "$ARCHIVE.sha256"

cleanup() {
  docker rm -f "$SOURCE_CONTAINER" "$REPLACEMENT_CONTAINER" >/dev/null 2>&1 || true
  docker volume rm "$SOURCE_VOLUME" "$REPLACEMENT_VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

wait_ready() {
  local name="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null 2>&1; then return 0; fi
    if ! docker inspect "$name" >/dev/null 2>&1; then
      echo "container ${name} disappeared before readiness" >&2
      return 1
    fi
    if [ "$(docker inspect --format '{{.State.Running}}' "$name")" != "true" ]; then
      echo "container ${name} exited before readiness" >&2
      docker logs "$name" >&2 || true
      return 1
    fi
    sleep 1
  done
  echo "container ${name} did not become ready" >&2
  docker logs "$name" >&2 || true
  return 1
}

prepare_volume() {
  local volume="$1"
  docker run --rm --user 0 -v "$volume:/data" "$IMAGE" sh -c 'chown 10001:10001 /data && chmod 0700 /data'
}

run_sara() {
  local name="$1" volume="$2"
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
    -e SARA_MODE=replacement-environment-drill \
    -p "127.0.0.1:${HOST_PORT}:9530" \
    -v "$volume:/var/lib/sara" \
    "$IMAGE" >/dev/null
}

inventory_volume() {
  local volume="$1" output="$2"
  docker run --rm --user 0 -v "$volume:/data:ro" "$IMAGE" python -c '
import hashlib,json,pathlib
root=pathlib.Path("/data"); rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    rows.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps(rows,sort_keys=True,indent=2))
' > "$output"
}

echo "[replacement] build tested source image"
docker build \
  --build-arg SARA_BUILD_COMMIT="$SOURCE_SHA" \
  --build-arg SARA_RELEASE_ID="replacement-drill-${SOURCE_SHA}" \
  -t "$IMAGE" "$ROOT" >/dev/null

docker volume create "$SOURCE_VOLUME" >/dev/null
prepare_volume "$SOURCE_VOLUME"
run_sara "$SOURCE_CONTAINER" "$SOURCE_VOLUME"
wait_ready "$SOURCE_CONTAINER"

python - "$MARKER" "$SOURCE_SHA" > "$OUT_DIR/marker-request.json" <<'PY'
import json,sys
marker, sha=sys.argv[1:]
print(json.dumps({"values":{"REPLACEMENT_RESTORE_MARKER":{"marker":marker,"written_by_commit":sha}}},sort_keys=True))
PY
curl -fsS -X PATCH \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H 'Content-Type: application/json' \
  --data-binary "@$OUT_DIR/marker-request.json" \
  "http://127.0.0.1:${HOST_PORT}/admin/registry" > "$OUT_DIR/source-registry.json"
inventory_volume "$SOURCE_VOLUME" "$OUT_DIR/source-inventory.json"

docker run --rm --user 0 -v "$SOURCE_VOLUME:/data:ro" "$IMAGE" python -c '
import pathlib,sys,tarfile
root=pathlib.Path("/data")
with tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz") as tf:
    for p in sorted(root.rglob("*")):
        tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
' > "$ARCHIVE"
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

docker rm -f "$SOURCE_CONTAINER" >/dev/null
docker volume rm "$SOURCE_VOLUME" >/dev/null
if docker inspect "$SOURCE_CONTAINER" >/dev/null 2>&1; then echo 'source container still exists' >&2; exit 1; fi
if docker volume inspect "$SOURCE_VOLUME" >/dev/null 2>&1; then echo 'source volume still exists' >&2; exit 1; fi

docker volume create "$REPLACEMENT_VOLUME" >/dev/null
prepare_volume "$REPLACEMENT_VOLUME"
docker run --rm --user 0 -i -v "$REPLACEMENT_VOLUME:/data" "$IMAGE" python -c '
import pathlib,sys,tarfile
root=pathlib.Path("/data"); root.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|gz") as tf:
    tf.extractall(root,filter="data")
' < "$ARCHIVE"

run_sara "$REPLACEMENT_CONTAINER" "$REPLACEMENT_VOLUME"
wait_ready "$REPLACEMENT_CONTAINER"
curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" > "$OUT_DIR/replacement-readyz.json"
curl -fsS "http://127.0.0.1:${HOST_PORT}/health" > "$OUT_DIR/replacement-health.json"
curl -fsS -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "http://127.0.0.1:${HOST_PORT}/admin/registry" > "$OUT_DIR/replacement-registry.json"
curl -fsS -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  "http://127.0.0.1:${HOST_PORT}/admin/selftest" > "$OUT_DIR/replacement-selftest.json"
inventory_volume "$REPLACEMENT_VOLUME" "$OUT_DIR/replacement-inventory.json"

export OUT_DIR SOURCE_SHA MARKER SOURCE_VOLUME REPLACEMENT_VOLUME ARCHIVE
python - <<'PY'
import datetime,hashlib,json,os,pathlib
root=pathlib.Path(os.environ['OUT_DIR'])
load=lambda n: json.loads((root/n).read_text(encoding='utf-8'))
source_inv=load('source-inventory.json')
replacement_inv=load('replacement-inventory.json')
registry=load('replacement-registry.json')['registry']
ready=load('replacement-readyz.json')
selftest=load('replacement-selftest.json')
health=load('replacement-health.json')
marker=registry['REPLACEMENT_RESTORE_MARKER']
archive=pathlib.Path(os.environ['ARCHIVE'])
checks={
  'source_and_replacement_volume_names_differ': os.environ['SOURCE_VOLUME'] != os.environ['REPLACEMENT_VOLUME'],
  'restored_file_inventory_matches_source': source_inv == replacement_inv,
  'synthetic_marker_preserved': marker.get('marker') == os.environ['MARKER'],
  'marker_origin_preserved': marker.get('written_by_commit') == os.environ['SOURCE_SHA'],
  'replacement_ready': ready.get('ok') is True and ready.get('status') == 'ready',
  'replacement_selftest_passed': selftest.get('ok') is True,
  'replacement_build_identity_matches_source': health.get('release_identity',{}).get('build_commit') == os.environ['SOURCE_SHA'],
}
record={
  'schema':'WS-SARA-REPLACEMENT-ENVIRONMENT-RESTORE-EVIDENCE-V1',
  'evidence_status':'INTERNAL_CI_GENERATED_UNSIGNED',
  'result':'PASS' if all(checks.values()) else 'FAIL',
  'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'source_build_commit':os.environ['SOURCE_SHA'],
  'source_volume_destroyed_before_restore':True,
  'source_volume_name':os.environ['SOURCE_VOLUME'],
  'replacement_volume_name':os.environ['REPLACEMENT_VOLUME'],
  'backup_sha256':'sha256:'+hashlib.sha256(archive.read_bytes()).hexdigest(),
  'checks':checks,
  'data_scope':'synthetic/public/releasable CI data only',
  'claims_boundary':(
    'This demonstrates restore into a clean, independently named replacement Docker runtime/volume after complete deletion '
    'of the original source container and volume on one GitHub-hosted runner. It is a replacement-environment precursor only. '
    'It does not establish recovery on a physically separate host or failure domain, site disaster recovery, hardware failure '
    'recovery, external custody, production RTO/RPO, customer acceptance, certification, or field readiness.'
  )
}
(root/'replacement-environment-restore.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
if record['result']!='PASS': raise SystemExit('REPLACEMENT_ENVIRONMENT_RESTORE: FAIL '+json.dumps(checks,sort_keys=True))
print('REPLACEMENT_ENVIRONMENT_RESTORE: PASS')
PY

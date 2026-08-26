#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT_DIR="${OPS_EVIDENCE_DIR:-operations_evidence}"
mkdir -p "$OUT_DIR"
HOST_PORT="${SARA_HOST_PORT:-$(awk -F= '$1=="SARA_HOST_PORT" {print $2}' .env 2>/dev/null || true)}"
HOST_PORT="${HOST_PORT:-9530}"

curl -fsS "http://127.0.0.1:${HOST_PORT}/livez" > "$OUT_DIR/livez.json"
curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" > "$OUT_DIR/readyz.json"
CONFIG_SHA="$(docker compose config | sha256sum | awk '{print $1}')"
CONTAINER_ID="$(docker compose ps -q sara)"
export OUT_DIR CONFIG_SHA CONTAINER_ID HOST_PORT
python - <<'PY'
import datetime, hashlib, json, os, pathlib, subprocess
out=pathlib.Path(os.environ['OUT_DIR'])
inspect=json.loads(subprocess.check_output(['docker','inspect',os.environ['CONTAINER_ID']], text=True))[0]
state=inspect.get('State',{})
image_id=inspect.get('Image','')
labels=(inspect.get('Config') or {}).get('Labels') or {}
record={
  'schema':'WS-SARA-OPS-SNAPSHOT-V2',
  'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'git_head':subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
  'compose_config_sha256':'sha256:'+os.environ['CONFIG_SHA'],
  'container_image_id':image_id,
  'release_identity':{
    'build_commit':labels.get('org.opencontainers.image.revision','UNKNOWN'),
    'release_id':labels.get('org.opencontainers.image.version','UNVERIFIED'),
    'image_title':labels.get('org.opencontainers.image.title','UNKNOWN')
  },
  'container_running':bool(state.get('Running')),
  'container_health':(state.get('Health') or {}).get('Status','not_configured'),
  'host_binding':'127.0.0.1:'+os.environ['HOST_PORT'],
  'livez_sha256':'sha256:'+hashlib.sha256((out/'livez.json').read_bytes()).hexdigest(),
  'readyz_sha256':'sha256:'+hashlib.sha256((out/'readyz.json').read_bytes()).hexdigest(),
  'data_scope':'synthetic/public/releasable only',
  'secret_material_in_snapshot':False,
  'external_compliance_claim':'NONE'
}
(out/'snapshot.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
PY

test -s "$OUT_DIR/snapshot.json"
python - <<'PY'
import json, pathlib, sys
record=json.loads(pathlib.Path('operations_evidence/snapshot.json').read_text())
identity=record['release_identity']
if identity['build_commit'] in ('UNKNOWN','') or identity['release_id'] in ('UNVERIFIED',''):
    raise SystemExit('release identity is not observable')
PY
echo "OPS_SNAPSHOT: PASS"

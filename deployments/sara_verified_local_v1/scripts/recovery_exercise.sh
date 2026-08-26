#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
RECOVERY_DIR="${RECOVERY_DIR:-recovery_evidence}"
export RECOVERY_DIR
mkdir -p "$RECOVERY_DIR"
rm -f "$RECOVERY_DIR"/sara-data.tar.gz "$RECOVERY_DIR"/before.json "$RECOVERY_DIR"/after.json "$RECOVERY_DIR"/result.json

docker compose up -d --build

docker compose run --rm --no-deps -v "$PWD/$RECOVERY_DIR:/recovery" --entrypoint python sara -c '
import hashlib,json,pathlib
root=pathlib.Path("/var/lib/sara"); rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()): rows.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
pathlib.Path("/recovery/before.json").write_text(json.dumps(rows,sort_keys=True,indent=2)+"\n")
'

docker compose run --rm --no-deps -v "$PWD/$RECOVERY_DIR:/recovery" --entrypoint python sara -c '
import pathlib,tarfile
root=pathlib.Path("/var/lib/sara")
with tarfile.open("/recovery/sara-data.tar.gz","w:gz") as tf:
    for p in sorted(root.rglob("*")): tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
'
sha256sum "$RECOVERY_DIR/sara-data.tar.gz" > "$RECOVERY_DIR/sara-data.tar.gz.sha256"

docker compose down -v
docker compose create sara >/dev/null
docker compose run --rm --no-deps -v "$PWD/$RECOVERY_DIR:/recovery" --entrypoint python sara -c '
import pathlib,tarfile
root=pathlib.Path("/var/lib/sara"); root.mkdir(parents=True,exist_ok=True)
with tarfile.open("/recovery/sara-data.tar.gz","r:gz") as tf: tf.extractall(root,filter="data")
'
docker compose up -d
for _ in $(seq 1 30); do if curl -fsS http://127.0.0.1:${SARA_HOST_PORT:-9530}/readyz >/dev/null; then break; fi; sleep 1; done
curl -fsS http://127.0.0.1:${SARA_HOST_PORT:-9530}/readyz >/dev/null

docker compose run --rm --no-deps -v "$PWD/$RECOVERY_DIR:/recovery" --entrypoint python sara -c '
import hashlib,json,pathlib
root=pathlib.Path("/var/lib/sara"); rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()): rows.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
pathlib.Path("/recovery/after.json").write_text(json.dumps(rows,sort_keys=True,indent=2)+"\n")
'
cmp "$RECOVERY_DIR/before.json" "$RECOVERY_DIR/after.json"
python - <<'PY'
import hashlib,json,pathlib,subprocess,datetime,os
p=pathlib.Path(os.environ["RECOVERY_DIR"]); archive=p/"sara-data.tar.gz"
result={"status":"PASS","exercise":"destructive_named_volume_backup_restore","archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"executed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"synthetic/public local deployment data only","external_compliance_claim":"NONE"}
(p/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
PY
echo "RECOVERY_EXERCISE: PASS"

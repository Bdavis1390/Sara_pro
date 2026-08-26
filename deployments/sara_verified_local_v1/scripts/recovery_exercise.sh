#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
RECOVERY_DIR="${RECOVERY_DIR:-recovery_evidence}"
export RECOVERY_DIR
HOST_PORT="${SARA_HOST_PORT:-$(awk -F= '$1=="SARA_HOST_PORT" {print $2}' .env 2>/dev/null || true)}"
HOST_PORT="${HOST_PORT:-9530}"
mkdir -p "$RECOVERY_DIR"
rm -f "$RECOVERY_DIR"/sara-data.tar.gz "$RECOVERY_DIR"/sara-data.tar.gz.sha256 "$RECOVERY_DIR"/before.json "$RECOVERY_DIR"/after.json "$RECOVERY_DIR"/result.json

docker compose up -d --build

# Recovery helpers run as root only to read/write the app-owned named volume.
# The runner owns all evidence files; helper output is streamed over stdio.
# The long-running SARA service remains UID 10001.
docker compose run --rm --no-deps --user 0 -T --entrypoint python sara -c '
import hashlib,json,pathlib
root=pathlib.Path("/var/lib/sara"); rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    rows.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps(rows,sort_keys=True,indent=2))
' > "$RECOVERY_DIR/before.json"

docker compose run --rm --no-deps --user 0 -T --entrypoint python sara -c '
import pathlib,sys,tarfile
root=pathlib.Path("/var/lib/sara")
with tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz") as tf:
    for p in sorted(root.rglob("*")):
        tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
' > "$RECOVERY_DIR/sara-data.tar.gz"
sha256sum "$RECOVERY_DIR/sara-data.tar.gz" > "$RECOVERY_DIR/sara-data.tar.gz.sha256"

docker compose down -v
docker compose create sara >/dev/null

docker compose run --rm --no-deps --user 0 -T --entrypoint python sara -c '
import pathlib,sys,tarfile
root=pathlib.Path("/var/lib/sara"); root.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|gz") as tf:
    tf.extractall(root,filter="data")
' < "$RECOVERY_DIR/sara-data.tar.gz"

docker compose up -d
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null

docker compose run --rm --no-deps --user 0 -T --entrypoint python sara -c '
import hashlib,json,pathlib
root=pathlib.Path("/var/lib/sara"); rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    rows.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps(rows,sort_keys=True,indent=2))
' > "$RECOVERY_DIR/after.json"

cmp "$RECOVERY_DIR/before.json" "$RECOVERY_DIR/after.json"
python - <<'PY'
import hashlib,json,pathlib,subprocess,datetime,os
p=pathlib.Path(os.environ["RECOVERY_DIR"]); archive=p/"sara-data.tar.gz"
result={
  "status":"PASS",
  "exercise":"destructive_named_volume_backup_restore",
  "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
  "git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
  "executed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "scope":"synthetic/public local deployment data only",
  "helper_privilege":"root for recovery helper containers only; SARA service remains non-root UID 10001",
  "external_compliance_claim":"NONE"
}
(p/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
PY
echo "RECOVERY_EXERCISE: PASS"

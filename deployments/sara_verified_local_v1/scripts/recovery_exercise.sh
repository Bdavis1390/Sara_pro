#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

RECOVERY_DIR="${RECOVERY_DIR:-recovery_evidence}"
export RECOVERY_DIR
HOST_PORT="${SARA_HOST_PORT:-$(awk -F= '$1=="SARA_HOST_PORT" {print $2}' .env 2>/dev/null || true)}"
HOST_PORT="${HOST_PORT:-9530}"
mkdir -p "$RECOVERY_DIR"
rm -f \
  "$RECOVERY_DIR"/sara-data.tar.gz \
  "$RECOVERY_DIR"/sara-data.tar.gz.sha256 \
  "$RECOVERY_DIR"/before.json \
  "$RECOVERY_DIR"/after.json \
  "$RECOVERY_DIR"/before-poo.json \
  "$RECOVERY_DIR"/after-poo.json \
  "$RECOVERY_DIR"/poststart-poo.json \
  "$RECOVERY_DIR"/mount-before.json \
  "$RECOVERY_DIR"/mount-after.json \
  "$RECOVERY_DIR"/result.json

wait_ready() {
  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  curl -fsS "http://127.0.0.1:${HOST_PORT}/readyz" >/dev/null
}

write_mount_evidence() {
  local container_id="$1"
  local output="$2"
  docker inspect "$container_id" | python3 -c '
import json,sys
records=json.load(sys.stdin)
if len(records) != 1:
    raise SystemExit("expected exactly one container inspection record")
mounts=[m for m in records[0].get("Mounts",[]) if m.get("Destination")=="/var/lib/sara"]
if len(mounts) != 1:
    raise SystemExit("expected exactly one /var/lib/sara mount")
m=mounts[0]
if m.get("Type") != "volume" or not m.get("Name"):
    raise SystemExit("/var/lib/sara must be backed by a named Docker volume")
print(json.dumps({
    "type":m.get("Type"),
    "name":m.get("Name"),
    "destination":m.get("Destination"),
    "rw":m.get("RW"),
},sort_keys=True,indent=2))
' > "$output"
}

inventory_named_volume() {
  local volume="$1"
  local image="$2"
  docker run --rm --user 0 -v "${volume}:/data:ro" --entrypoint python "$image" -c '
import hashlib,json,pathlib
root=pathlib.Path("/data")
rows=[]
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    rows.append({
        "path":str(p.relative_to(root)),
        "size":p.stat().st_size,
        "sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
    })
print(json.dumps(rows,sort_keys=True,indent=2))
'
}

poo_snapshot_named_volume() {
  local volume="$1"
  local image="$2"
  docker run --rm --user 0 -v "${volume}:/data:ro" --entrypoint python "$image" -c '
import json,pathlib
path=pathlib.Path("/data/registry.json")
if not path.is_file():
    raise SystemExit("registry.json missing from SARA volume")
registry=json.loads(path.read_text(encoding="utf-8"))
poo=registry.get("POO_TECHNICAL_REGISTRY")
if not isinstance(poo,dict):
    raise SystemExit("POO_TECHNICAL_REGISTRY missing from populated deployment")
states=poo.get("states")
commits=poo.get("commits")
if not isinstance(states,list) or not isinstance(commits,dict):
    raise SystemExit("PoO technical registry has invalid state/commit collections")
smoke=[s for s in states if isinstance(s,dict) and s.get("asset_id")=="asset:deployment-smoke"]
if len(smoke) != 1:
    raise SystemExit("deployment-smoke PoO state missing or duplicated")
state=smoke[0]
for field in ("legal_title_established","live_value_authorized","external_transfer_executed"):
    if state.get(field) is not False:
        raise SystemExit(f"PoO deployment-smoke authority boundary violated: {field}")
print(json.dumps({
    "schema":poo.get("schema"),
    "registry_schema":poo.get("registry_schema"),
    "registry_digest":poo.get("registry_digest"),
    "state_count":len(states),
    "commit_count":len(commits),
    "deployment_smoke_state_digest":state.get("active_poo_digest"),
    "deployment_smoke_present":True,
},sort_keys=True,indent=2))
'
}

# verify_deployment.sh populates the SARA registry before this exercise. Start
# the exact Compose service, resolve the ACTUAL /var/lib/sara named volume from
# the running container, then quiesce the service before taking authoritative
# bytes. This avoids both helper-volume ambiguity and audit-log write races.
docker compose up -d --build
wait_ready
live_container="$(docker compose ps -q sara)"
[[ -n "$live_container" ]] || { echo "ERROR: SARA container is not running." >&2; exit 1; }
write_mount_evidence "$live_container" "$RECOVERY_DIR/mount-before.json"
source_volume="$(python3 - "$RECOVERY_DIR/mount-before.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding="utf-8"))["name"])
PY
)"
source_image="$(docker inspect --format '{{.Config.Image}}' "$live_container")"
[[ -n "$source_volume" && -n "$source_image" ]] || { echo "ERROR: Source volume/image resolution failed." >&2; exit 1; }

docker compose stop sara >/dev/null
inventory_named_volume "$source_volume" "$source_image" > "$RECOVERY_DIR/before.json"
poo_snapshot_named_volume "$source_volume" "$source_image" > "$RECOVERY_DIR/before-poo.json"
python3 - "$RECOVERY_DIR/before.json" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1],encoding="utf-8"))
paths={row.get("path") for row in rows if isinstance(row,dict)}
required={"registry.json","audit.jsonl"}
missing=sorted(required-paths)
if missing:
    raise SystemExit("populated recovery source is missing: " + ", ".join(missing))
if not rows:
    raise SystemExit("recovery source inventory must not be empty")
PY

# Back up the exact quiesced volume through an explicitly named, read-only
# mount. Root is used only for bounded backup/restore access; SARA runs UID 10001.
docker run --rm --user 0 -v "${source_volume}:/data:ro" --entrypoint python "$source_image" -c '
import pathlib,sys,tarfile
root=pathlib.Path("/data")
with tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz") as tf:
    for p in sorted(root.rglob("*")):
        tf.add(p,arcname=str(p.relative_to(root)),recursive=False)
' > "$RECOVERY_DIR/sara-data.tar.gz"
sha256sum "$RECOVERY_DIR/sara-data.tar.gz" > "$RECOVERY_DIR/sara-data.tar.gz.sha256"

# Hard destruction boundary: remove the Compose service and its source volume,
# then create a fresh service/volume and restore only from the exported archive.
docker compose down -v
docker compose create sara >/dev/null
restore_container="$(docker compose ps -aq sara | head -n1)"
[[ -n "$restore_container" ]] || { echo "ERROR: Could not create SARA restore container." >&2; exit 1; }
write_mount_evidence "$restore_container" "$RECOVERY_DIR/mount-after.json"
restore_volume="$(python3 - "$RECOVERY_DIR/mount-after.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1],encoding="utf-8"))["name"])
PY
)"
restore_image="$(docker inspect --format '{{.Config.Image}}' "$restore_container")"
[[ -n "$restore_volume" && -n "$restore_image" ]] || { echo "ERROR: Restore volume/image resolution failed." >&2; exit 1; }

docker run --rm -i --user 0 \
  -v "${restore_volume}:/var/lib/sara" \
  --entrypoint python "$restore_image" -c '
import os,pathlib,sys,tarfile
root=pathlib.Path("/var/lib/sara")
root.mkdir(parents=True,exist_ok=True)
with tarfile.open(fileobj=sys.stdin.buffer,mode="r|gz") as tf:
    tf.extractall(root,filter="data")
for p in [root,*root.rglob("*")]:
    try:
        os.chown(p,10001,10001)
    except FileNotFoundError:
        pass
' < "$RECOVERY_DIR/sara-data.tar.gz"

# Compare restored bytes BEFORE service startup, because normal startup appends
# a new service_started audit record and should not be mistaken for corruption.
inventory_named_volume "$restore_volume" "$restore_image" > "$RECOVERY_DIR/after.json"
poo_snapshot_named_volume "$restore_volume" "$restore_image" > "$RECOVERY_DIR/after-poo.json"
cmp "$RECOVERY_DIR/before.json" "$RECOVERY_DIR/after.json"
cmp "$RECOVERY_DIR/before-poo.json" "$RECOVERY_DIR/after-poo.json"

# Now prove the restored volume is the one used by the restarted service and
# that startup leaves the PoO technical registry semantically unchanged.
docker compose up -d
wait_ready
restored_container="$(docker compose ps -q sara)"
[[ -n "$restored_container" ]] || { echo "ERROR: Restored SARA container is not running." >&2; exit 1; }
restored_volume="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/var/lib/sara"}}{{.Name}}{{end}}{{end}}' "$restored_container")"
[[ "$restored_volume" == "$restore_volume" ]] || {
  echo "ERROR: Running restored service is not using the restored named volume." >&2
  exit 1
}
poo_snapshot_named_volume "$restore_volume" "$restore_image" > "$RECOVERY_DIR/poststart-poo.json"
cmp "$RECOVERY_DIR/before-poo.json" "$RECOVERY_DIR/poststart-poo.json"

python3 - <<'PY'
import datetime,hashlib,json,os,pathlib,subprocess
p=pathlib.Path(os.environ["RECOVERY_DIR"])
archive=p/"sara-data.tar.gz"
before=json.loads((p/"before.json").read_text(encoding="utf-8"))
poo=json.loads((p/"before-poo.json").read_text(encoding="utf-8"))
mount_before=json.loads((p/"mount-before.json").read_text(encoding="utf-8"))
mount_after=json.loads((p/"mount-after.json").read_text(encoding="utf-8"))
result={
  "status":"PASS",
  "exercise":"destructive_named_volume_backup_restore",
  "archive_sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),
  "git_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
  "executed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "scope":"synthetic/public local deployment data only",
  "helper_privilege":"root only for bounded backup/restore access; SARA service remains non-root UID 10001",
  "source_file_count":len(before),
  "source_volume_name":mount_before["name"],
  "restored_volume_name":mount_after["name"],
  "source_volume_destroyed_before_restore":True,
  "poo_registry_digest":poo["registry_digest"],
  "poo_state_count":poo["state_count"],
  "poo_commit_count":poo["commit_count"],
  "deployment_smoke_state_preserved":poo["deployment_smoke_present"],
  "byte_identical_prestart_inventory_after_restore":True,
  "poo_snapshot_identical_prestart_after_restore":True,
  "poo_snapshot_unchanged_after_service_restart":True,
  "external_compliance_claim":"NONE",
}
(p/"result.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
PY

echo "RECOVERY_EXERCISE: PASS"

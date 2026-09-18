#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${SDA_ADAPTER_G3_EVIDENCE_DIR:-$ROOT/sda_adapter_g3_evidence}"
SOURCE_SHA="${GITHUB_SHA:-$(git -C "$ROOT" rev-parse HEAD)}"
RUN_KEY="${GITHUB_RUN_ID:-local}-$$"
SAFE_KEY="${RUN_KEY//[^a-zA-Z0-9_.-]/_}"
IMAGE="ws-sda-adapter-g3:${SOURCE_SHA:0:12}"
CONTAINER="ws-sda-adapter-g3-${SAFE_KEY}"
HOST_SECRET="host-secret-must-not-cross-adapter-boundary"

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/*.json "$OUT_DIR"/*.txt

cleanup() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    echo "SDA G3B adapter isolation drill failed" >&2
    docker inspect "$CONTAINER" >&2 2>/dev/null || true
    docker logs "$CONTAINER" >&2 2>/dev/null || true
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[g3b] build exact tested SARA image"
docker build   --build-arg SARA_BUILD_COMMIT="$SOURCE_SHA"   --build-arg SARA_RELEASE_ID="sda-adapter-g3-${SOURCE_SHA}"   -t "$IMAGE" "$ROOT" >/dev/null

export WS_PARENT_SECRET="$HOST_SECRET"

read -r -d '' PROBE_CODE <<'PY' || true
import json
import os
import pathlib
import socket

checks = {}

checks["non_root_uid"] = os.geteuid() != 0
checks["parent_secret_absent"] = os.getenv("WS_PARENT_SECRET") is None

root_write_blocked = False
try:
    pathlib.Path("/app/g3b-must-not-write").write_text("x", encoding="utf-8")
except OSError:
    root_write_blocked = True
checks["root_filesystem_write_blocked"] = root_write_blocked

scratch = pathlib.Path("/tmp/g3b-scratch")
scratch.write_text("ok", encoding="utf-8")
checks["tmpfs_scratch_writable"] = scratch.read_text(encoding="utf-8") == "ok"

external_connect_blocked = False
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(0.5)
try:
    sock.connect(("1.1.1.1", 53))
except OSError:
    external_connect_blocked = True
finally:
    sock.close()
checks["external_network_connect_blocked"] = external_connect_blocked

interfaces = [name for _index, name in socket.if_nameindex()]
checks["only_loopback_interface_present"] = set(interfaces).issubset({"lo"})

record = {
    "schema": "WS-SDA-ADAPTER-CONTAINER-ISOLATION-RUNTIME-V1",
    "checks": checks,
    "interfaces": interfaces,
    "effective_uid": os.geteuid(),
    "environment_keys": sorted(os.environ),
}
print(json.dumps(record, sort_keys=True))
if not all(checks.values()):
    raise SystemExit(17)
PY

docker create   --name "$CONTAINER"   --network none   --read-only   --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m   --security-opt no-new-privileges:true   --cap-drop ALL   --pids-limit 32   --memory 128m   --cpus 0.50   --user 10001:10001   --no-healthcheck   "$IMAGE"   python -c "$PROBE_CODE" >/dev/null

docker start -a "$CONTAINER" > "$OUT_DIR/runtime-probe.json"

docker inspect "$CONTAINER" > "$OUT_DIR/container-inspect.json"
docker image inspect "$IMAGE" > "$OUT_DIR/image-inspect.json"

export OUT_DIR SOURCE_SHA HOST_SECRET CONTAINER IMAGE
python - <<'PY'
import datetime
import hashlib
import json
import os
import pathlib

root = pathlib.Path(os.environ["OUT_DIR"])
runtime = json.loads((root / "runtime-probe.json").read_text(encoding="utf-8"))
container = json.loads((root / "container-inspect.json").read_text(encoding="utf-8"))[0]
image = json.loads((root / "image-inspect.json").read_text(encoding="utf-8"))[0]

host = container["HostConfig"]
config = container["Config"]
labels = image.get("Config", {}).get("Labels", {}) or {}

tmpfs = host.get("Tmpfs") or {}
security_opt = host.get("SecurityOpt") or []
cap_drop = host.get("CapDrop") or []
port_bindings = host.get("PortBindings") or {}

checks = {
    "runtime_probe_passed": all(runtime["checks"].values()),
    "network_mode_none": host.get("NetworkMode") == "none",
    "readonly_rootfs": host.get("ReadonlyRootfs") is True,
    "no_new_privileges": any(
        item in {"no-new-privileges", "no-new-privileges:true"}
        for item in security_opt
    ),
    "all_capabilities_dropped": "ALL" in cap_drop,
    "pids_limit_32": host.get("PidsLimit") == 32,
    "memory_limit_128m": host.get("Memory") == 128 * 1024 * 1024,
    "cpu_limit_half_core": host.get("NanoCpus") == 500_000_000,
    "non_root_user_fixed": config.get("User") == "10001:10001",
    "tmpfs_only_scratch_present": "/tmp" in tmpfs,
    "no_host_port_bindings": port_bindings == {},
    "no_host_mounts": len(container.get("Mounts") or []) == 0,
    "host_secret_not_configured": all(
        not item.startswith("WS_PARENT_SECRET=")
        for item in (config.get("Env") or [])
    ),
    "image_bound_to_exact_source_commit": labels.get(
        "org.opencontainers.image.revision"
    ) == os.environ["SOURCE_SHA"],
}

evidence = {
    "schema": "WS-SDA-ADAPTER-CONTAINER-ISOLATION-EVIDENCE-V1",
    "evidence_status": "INTERNAL_CI_REFERENCE_ISOLATION",
    "result": "PASS" if all(checks.values()) else "FAIL",
    "executed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_build_commit": os.environ["SOURCE_SHA"],
    "checks": checks,
    "runtime": runtime,
    "container_controls": {
        "network_mode": host.get("NetworkMode"),
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "security_opt": security_opt,
        "cap_drop": cap_drop,
        "pids_limit": host.get("PidsLimit"),
        "memory_bytes": host.get("Memory"),
        "nano_cpus": host.get("NanoCpus"),
        "user": config.get("User"),
        "tmpfs": tmpfs,
        "port_bindings": port_bindings,
        "mount_count": len(container.get("Mounts") or []),
    },
    "claims_boundary": (
        "This evidence validates a bounded Docker reference adapter environment: "
        "network=none, read-only root filesystem, tmpfs scratch, non-root UID, "
        "no-new-privileges, all Linux capabilities dropped, PID/memory/CPU limits, "
        "no host mounts or host ports, and no inherited test secret. It does not "
        "establish VM/microVM isolation, a custom seccomp profile, AppArmor/SELinux "
        "policy, protection from Docker/kernel/runtime vulnerabilities, production "
        "key or secrets governance, independent penetration testing, accreditation, "
        "or classified-network authorization."
    ),
}
evidence["artifact_sha256"] = {
    name: "sha256:" + hashlib.sha256((root / name).read_bytes()).hexdigest()
    for name in ("runtime-probe.json", "container-inspect.json", "image-inspect.json")
}
(root / "g3b-evidence.json").write_text(
    json.dumps(evidence, sort_keys=True, indent=2) + "\n",
    encoding="utf-8",
)
if evidence["result"] != "PASS":
    raise SystemExit("WS-SDA G3B: FAIL " + json.dumps(checks, sort_keys=True))
print("WS-SDA G3B: PASS")
PY

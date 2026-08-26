#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

host_port="${SARA_HOST_PORT:-9530}"
base_url="${SARA_BASE_URL:-http://127.0.0.1:${host_port}}"
export SARA_BASE_URL="${base_url}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
evidence_root=".deployment-evidence"
evidence_dir="${evidence_root}/${stamp}"

if [[ -e "$evidence_root" ]]; then
  if [[ ! -d "$evidence_root" ]]; then
    echo "ERROR: Evidence root exists but is not a directory: ${evidence_root}" >&2
    exit 1
  fi
  chmod 0700 "$evidence_root"
else
  if ! mkdir -m 0700 "$evidence_root"; then
    echo "ERROR: Could not create evidence root: ${evidence_root}" >&2
    exit 1
  fi
fi

if ! mkdir -m 0700 "$evidence_dir"; then
  if [[ -e "$evidence_dir" ]]; then
    echo "ERROR: Evidence directory already exists: ${evidence_dir}" >&2
  else
    echo "ERROR: Could not create evidence directory: ${evidence_dir}" >&2
  fi
  exit 1
fi

git_head="$(git rev-parse HEAD 2>/dev/null || echo unknown)"

# Build a live inventory from every Git-tracked file in this deployment subtree.
# This supersedes the historical static file-hash list in MANIFEST.json and binds
# deployment evidence to the files actually present at the tested commit.
tracked_files_sha256="$(
  python3 - "$evidence_dir/tracked-files.json" <<'PY_TRACKED'
import hashlib
import json
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1])
raw = subprocess.check_output(["git", "ls-files", "-z", "--", "."])
paths = sorted(p.decode("utf-8") for p in raw.split(b"\0") if p)
records = []
for value in paths:
    path = Path(value)
    data = path.read_bytes()
    records.append(
        {
            "path": value,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }
    )
payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
out.write_text(json.dumps({"schema": "WS-TRACKED-SUBTREE-INVENTORY-V1", "files": records}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(hashlib.sha256(payload).hexdigest())
PY_TRACKED
)"

manifest_metadata_sha256="$(sha256sum MANIFEST.json | awk '{print $1}')"

if git diff --quiet -- . && git diff --cached --quiet -- .; then
  tracked_worktree_state="clean"
else
  tracked_worktree_state="dirty"
fi

{
  echo "timestamp_utc=${stamp}"
  echo "git_head=${git_head}"
  echo "tracked_worktree_state=${tracked_worktree_state}"
  echo "tracked_files_sha256=${tracked_files_sha256}"
  echo "manifest_metadata_sha256=${manifest_metadata_sha256}"
  echo "docker_version=$(docker --version)"
  echo "compose_version=$(docker compose version)"
  echo "sara_host_port=${host_port}"
  echo "sara_base_url=${base_url}"
} > "${evidence_dir}/baseline.txt"

redacted_compose="$(mktemp)"
trap 'rm -f "$redacted_compose"' EXIT
docker compose config | awk '
  /^[[:space:]]*SARA_ADMIN_TOKEN:[[:space:]]*/ {
    sub(/:.*/, ": \"<REDACTED>\"")
    admin_tokens++
  }
  /^[[:space:]]*SARA_RELAY_TOKEN:[[:space:]]*/ {
    sub(/:.*/, ": \"<REDACTED>\"")
    relay_tokens++
  }
  { print }
  END {
    if (admin_tokens != 1 || relay_tokens != 1) {
      print "ERROR: Compose token redaction did not find exactly one value for each token." > "/dev/stderr"
      exit 1
    }
  }
' > "$redacted_compose"
mv "$redacted_compose" "${evidence_dir}/compose.rendered.yaml"
trap - EXIT

docker compose build --pull | tee "${evidence_dir}/build.log"
docker compose up -d

wait_for_healthy() {
  local container_id health
  container_id="$(docker compose ps -q sara)"
  [[ -n "$container_id" ]] || return 1
  for attempt in $(seq 1 30); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
    if [[ "$health" == "healthy" ]]; then
      return 0
    fi
    echo "Docker health attempt ${attempt}/30: ${health}..."
    sleep 2
  done
  return 1
}

if ! wait_for_healthy; then
  echo "ERROR: Docker did not report SARA healthy after startup." >&2
  docker compose ps -a >&2
  docker compose logs --no-color --tail=100 sara >&2
  exit 1
fi

initial_ready=0
for _ in $(seq 1 30); do
  if curl --fail --silent "${base_url}/readyz" > "${evidence_dir}/health.initial.json"; then
    initial_ready=1
    break
  fi
  sleep 2
done
if [[ "$initial_ready" -ne 1 ]]; then
  echo "ERROR: Readiness endpoint did not pass after Docker became healthy." >&2
  exit 1
fi

scripts/admin_smoke_test.sh | tee "${evidence_dir}/smoke.initial.log"
docker compose restart sara

echo "Waiting for SARA health after restart..."
restart_ready=0

if wait_for_healthy && curl --fail --silent "${base_url}/readyz" \
  > "${evidence_dir}/health.after-restart.json" 2>/dev/null; then
  restart_ready=1
fi

if [ "${restart_ready}" -ne 1 ]; then
  echo "ERROR: SARA did not become healthy after restart." >&2
  docker compose ps -a >&2
  docker compose logs --no-color --tail=100 sara >&2
  exit 1
fi

curl --fail --silent --show-error -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  "${base_url}/admin/registry" | tee "${evidence_dir}/registry.after-restart.json" | grep -q "SARA_CORE"
scripts/admin_smoke_test.sh | tee "${evidence_dir}/smoke.after-restart.log"

if ! wait_for_healthy; then
  echo "ERROR: Docker health was not healthy before evidence capture." >&2
  exit 1
fi

docker compose ps > "${evidence_dir}/compose.ps.txt"
docker compose logs --no-color > "${evidence_dir}/service.log"

sha256sum "${evidence_dir}"/* > "${evidence_dir}/SHA256SUMS"
echo "Verified deployment evidence: ${evidence_dir}"

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
manifest_files_sha256="$(
  python3 - <<'PY_MANIFEST'
import hashlib
import json
from pathlib import Path

manifest = json.loads(
    Path("MANIFEST.json").read_text(encoding="utf-8")
)
payload = json.dumps(
    manifest["files"],
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
print(hashlib.sha256(payload).hexdigest())
PY_MANIFEST
)"

if git diff --quiet -- .   && git diff --cached --quiet -- .   && [[ -z "$(git ls-files --others --exclude-standard)" ]]; then
  git_worktree_state="clean"
else
  git_worktree_state="dirty"
fi

{
  echo "timestamp_utc=${stamp}"
  echo "git_head=${git_head}"
  echo "git_worktree_state=${git_worktree_state}"
  echo "manifest_files_sha256=${manifest_files_sha256}"
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

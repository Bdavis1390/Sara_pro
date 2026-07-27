#!/usr/bin/env bash
set -euo pipefail

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
evidence_dir=".deployment-evidence/${stamp}"
mkdir -p "$evidence_dir"

{
  echo "timestamp_utc=${stamp}"
  echo "git_commit=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "docker_version=$(docker --version)"
  echo "compose_version=$(docker compose version)"
  echo "sara_host_port=${host_port}"
  echo "sara_base_url=${base_url}"
} > "${evidence_dir}/baseline.txt"

docker compose config > "${evidence_dir}/compose.rendered.yaml"
docker compose build --pull | tee "${evidence_dir}/build.log"
docker compose up -d

for _ in $(seq 1 30); do
  if curl --fail --silent ${base_url}/health > "${evidence_dir}/health.initial.json"; then
    break
  fi
  sleep 2
done

scripts/admin_smoke_test.sh | tee "${evidence_dir}/smoke.initial.log"
docker compose restart sara

echo "Waiting for SARA health after restart..."
restart_ready=0

for attempt in $(seq 1 30); do
  if curl --fail --silent ${base_url}/health > "${evidence_dir}/health.after-restart.json" 2>/dev/null; then
    restart_ready=1
    break
  fi

  echo "Restart health attempt ${attempt}/30..."
  sleep 2
done

if [ "${restart_ready}" -ne 1 ]; then
  echo "ERROR: SARA did not become healthy after restart." >&2
  docker compose ps -a >&2
  docker compose logs --no-color --tail=100 sara >&2
  exit 1
fi
curl --fail --silent --show-error -H "Authorization: Bearer ${SARA_ADMIN_TOKEN}" \
  ${base_url}/admin/registry | tee "${evidence_dir}/registry.after-restart.json" | grep -q "SARA_CORE"
scripts/admin_smoke_test.sh | tee "${evidence_dir}/smoke.after-restart.log"
docker compose ps > "${evidence_dir}/compose.ps.txt"
docker compose logs --no-color > "${evidence_dir}/service.log"

sha256sum "${evidence_dir}"/* > "${evidence_dir}/SHA256SUMS"
echo "Verified deployment evidence: ${evidence_dir}"

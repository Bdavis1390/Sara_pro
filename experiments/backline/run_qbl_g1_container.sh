#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${WS_QBL_IMAGE:-worldshepherd-qbl-g1:v0.1}"
EVIDENCE_ROOT="${WS_QBL_EVIDENCE_ROOT:-$HOME/worldshepherd-evidence/backline}"
RUN_ID="qbl-$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="${EVIDENCE_ROOT}/${RUN_ID}"

mkdir -p "${RUN_DIR}"

printf 'QBL run: %s\n' "${RUN_ID}"
printf 'Evidence: %s\n' "${RUN_DIR}"
printf 'Image: %s\n' "${IMAGE_NAME}"

# Build from the repository root so the Dockerfile can COPY the experiment harnesses.
docker build \
  --file experiments/backline/Dockerfile.qbl-g1 \
  --tag "${IMAGE_NAME}" \
  . 2>&1 | tee "${RUN_DIR}/docker-build.log"

# Preserve image metadata before execution.
docker image inspect "${IMAGE_NAME}" > "${RUN_DIR}/docker-image-inspect.json"

set +e
docker run --rm \
  "${IMAGE_NAME}" \
  python /workspace/backline_cpu_cpu.py --repeat 10 --json \
  > "${RUN_DIR}/qbl-g1.json" \
  2> "${RUN_DIR}/qbl-g1.stderr.log"
G1_RC=$?
set -e

if [[ ${G1_RC} -ne 0 ]]; then
  printf 'QBL-G1 failed with exit code %d. Evidence retained at %s\n' "${G1_RC}" "${RUN_DIR}" >&2
  exit "${G1_RC}"
fi

set +e
docker run --rm \
  --volume "${RUN_DIR}:/evidence" \
  "${IMAGE_NAME}" \
  python /workspace/backline_benchmark.py \
    --warmup 3 \
    --iterations 100 \
    --output /evidence/qbl-g2.json \
  > "${RUN_DIR}/qbl-g2.stdout.log" \
  2> "${RUN_DIR}/qbl-g2.stderr.log"
G2_RC=$?
set -e

sha256sum \
  experiments/backline_cpu_cpu.py \
  experiments/backline_benchmark.py \
  experiments/backline/Dockerfile.qbl-g1 \
  > "${RUN_DIR}/worldshepherd-input-sha256.txt"

git rev-parse HEAD > "${RUN_DIR}/sara-pro-commit.txt"
git status --short > "${RUN_DIR}/sara-pro-status.txt"

printf 'QBL-G1 PASS. QBL-G2 exit code: %d\n' "${G2_RC}"
printf 'Evidence retained outside the public repository: %s\n' "${RUN_DIR}"

exit "${G2_RC}"

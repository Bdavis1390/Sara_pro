#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing. Copy .env.example to .env and replace both token values." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

python - <<'PY'
from worldshepherd_sara.auth import validate_runtime_secrets
validate_runtime_secrets()
print("Token validation: OK")
PY

exec python -m worldshepherd_sara

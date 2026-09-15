#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements-worldshepherd.txt

if [ ! -f ".env" ]; then
  ADMIN_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  RELAY_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  cat > .env <<EOF
SARA_ADMIN_TOKEN=$ADMIN_TOKEN
SARA_RELAY_TOKEN=$RELAY_TOKEN
SARA_DATA_DIR=data
EOF
  echo "Created .env with fresh local tokens."
fi

set -a
source .env
set +a

echo "Starting Worldshepherd SARA interface:"
echo "  UI:       http://localhost:9530/ui"
echo "  Health:   http://localhost:9530/health"
echo "  Evidence: http://localhost:9530/v1/evidence/metrics"
echo
echo "Use SARA_ADMIN_TOKEN from .env for admin access."

exec uvicorn worldshepherd_sara.evidence_server:app --host 127.0.0.1 --port 9530

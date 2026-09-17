#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_USER="ws-qphonon"
CODE_DIR="/opt/worldshepherd/qphonon"
STATE_DIR="/var/lib/worldshepherd/qphonon"
CONFIG_DIR="/etc/worldshepherd/qphonon"

command -v python3 >/dev/null
command -v ssh-keygen >/dev/null

if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --home-dir "${STATE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

install -d -o root -g root -m 0755 /opt/worldshepherd
install -d -o root -g root -m 0755 "${CODE_DIR}"
install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0700 "${STATE_DIR}"
install -d -o root -g "${SERVICE_USER}" -m 0750 "${CONFIG_DIR}"

find "${ROOT}/tools/qphonon" -maxdepth 1 -type f -name '*.py' -print0 |
  while IFS= read -r -d '' file; do
    install -o root -g root -m 0644 "${file}" "${CODE_DIR}/$(basename "${file}")"
  done

if [[ ! -e "${CONFIG_DIR}/allowed_signers" ]]; then
  install -o root -g "${SERVICE_USER}" -m 0440 /dev/null "${CONFIG_DIR}/allowed_signers"
fi

cat >/usr/local/bin/ws-qphonon-guard <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec /usr/bin/python3 /opt/worldshepherd/qphonon/deployment_guard.py   --state-db /var/lib/worldshepherd/qphonon/state.sqlite3 "$@"
EOF
chmod 0755 /usr/local/bin/ws-qphonon-guard
chown root:root /usr/local/bin/ws-qphonon-guard

cat <<EOF
Installed WS-QPHONON guard infrastructure.

Next mandatory steps:
1. Add trusted public signing identities to:
   ${CONFIG_DIR}/allowed_signers
2. Keep corresponding private keys outside this host/guard boundary.
3. Invoke the guard as ${SERVICE_USER} or through a separately governed SARA launcher.
4. Do not connect this guard directly to hardware actuation.
EOF

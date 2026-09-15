#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${ROOT_DIR}/deployments/sara_verified_local_v1"
VENV_DIR="${RUNTIME_DIR}/.venv"
ENV_FILE="${RUNTIME_DIR}/.env"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

runtime_python() {
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    printf '%s\n' "${VENV_DIR}/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    fail "Python 3 is required."
  fi
}

check_runtime() {
  local required=(
    "README.md"
    "pyproject.toml"
    "constraints-runtime.txt"
    "constraints-ci.txt"
    ".env.example"
    "worldshepherd_sara/__init__.py"
    "worldshepherd_sara/__main__.py"
    "worldshepherd_sara/app.py"
    "worldshepherd_sara/auth.py"
    "scripts/start_interface.sh"
    "scripts/admin_smoke_test.sh"
    "tests/test_api.py"
  )
  local item
  for item in "${required[@]}"; do
    [[ -f "${RUNTIME_DIR}/${item}" ]] || fail "Canonical runtime is missing ${item}"
  done
  printf 'Canonical runtime: OK\n%s\n' "${RUNTIME_DIR}"
}

setup_runtime() {
  check_runtime >/dev/null
  local bootstrap_python="${PYTHON:-python3}"
  command -v "${bootstrap_python}" >/dev/null 2>&1 || fail "${bootstrap_python} is required."

  "${bootstrap_python}" -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install 'pip==26.2.1'
  "${VENV_DIR}/bin/python" -m pip install \
    -c "${RUNTIME_DIR}/constraints-ci.txt" \
    -e "${RUNTIME_DIR}[test]"
  "${VENV_DIR}/bin/python" -m pip check

  if [[ ! -f "${ENV_FILE}" ]]; then
    local relay_token admin_token commit short_commit
    relay_token="$("${VENV_DIR}/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')"
    admin_token="$("${VENV_DIR}/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))')"
    commit="$(git -C "${ROOT_DIR}" rev-parse HEAD 2>/dev/null || printf 'UNKNOWN')"
    short_commit="${commit:0:12}"

    cat >"${ENV_FILE}" <<EOF
SARA_RELAY_TOKEN=${relay_token}
SARA_ADMIN_TOKEN=${admin_token}
SARA_BIND_HOST=127.0.0.1
SARA_PORT=9530
SARA_HOST_PORT=9530
SARA_DATA_DIR=./data
SARA_MODE=local-verified
SARA_LOG_LEVEL=info
SARA_BUILD_COMMIT=${commit}
SARA_RELEASE_ID=local-${short_commit}
PRIME_SENTINEL_PUBLIC_KEYS_JSON={}
PRIME_SENTINEL_REVOKED_KEY_IDS=
PRIME_SENTINEL_HOST_PORT=9540
EOF
    chmod 600 "${ENV_FILE}"
    printf 'Created %s with independent random relay/admin tokens.\n' "${ENV_FILE}"
  else
    printf 'Preserving existing %s (not overwritten).\n' "${ENV_FILE}"
  fi

  printf '\nSetup complete. Start SARA with:\n  bash scripts/sara.sh run\n'
}

run_runtime() {
  check_runtime >/dev/null
  [[ -x "${VENV_DIR}/bin/python" ]] || fail "Runtime virtual environment is missing. Run: bash scripts/sara.sh setup"
  [[ -f "${ENV_FILE}" ]] || fail "Runtime .env is missing. Run: bash scripts/sara.sh setup"
  export PATH="${VENV_DIR}/bin:${PATH}"
  exec bash "${RUNTIME_DIR}/scripts/start_interface.sh"
}

test_runtime() {
  check_runtime >/dev/null
  local python_bin
  python_bin="$(runtime_python)"
  cd "${RUNTIME_DIR}"
  exec "${python_bin}" -m pytest "$@"
}

smoke_runtime() {
  check_runtime >/dev/null
  [[ -f "${ENV_FILE}" ]] || fail "Runtime .env is missing. Run: bash scripts/sara.sh setup"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  exec bash "${RUNTIME_DIR}/scripts/admin_smoke_test.sh"
}

usage() {
  cat <<'EOF'
Usage: bash scripts/sara.sh <command> [args]

Commands:
  setup        Create/update the isolated runtime venv and create .env if absent
  run          Start the canonical local SARA / SSPADAWANZZ service
  test [args]  Run the canonical pytest suite (optional pytest args accepted)
  smoke        Run the admin smoke test against an already-running local service
  check        Verify required canonical runtime entry-point files exist
  path         Print the canonical runtime path
  help         Show this help
EOF
}

command_name="${1:-help}"
shift || true

case "${command_name}" in
  setup) setup_runtime "$@" ;;
  run) run_runtime "$@" ;;
  test) test_runtime "$@" ;;
  smoke) smoke_runtime "$@" ;;
  check) check_runtime "$@" ;;
  path) printf '%s\n' "${RUNTIME_DIR}" ;;
  help|-h|--help) usage ;;
  *) usage >&2; fail "Unknown command: ${command_name}" ;;
esac

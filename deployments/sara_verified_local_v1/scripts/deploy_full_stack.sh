#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

for command_name in docker openssl curl python3 git; do
  require_command "$command_name"
done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is required"

if ! git diff --quiet -- . || ! git diff --cached --quiet -- .; then
  fail "tracked deployment subtree is dirty; commit or revert changes before deployment"
fi

git_head="$(git rev-parse HEAD)"
[[ "$git_head" =~ ^[0-9a-f]{40}$ ]] || fail "unable to resolve exact Git commit"
short_head="${git_head:0:12}"
release_id="${WS_DEPLOY_RELEASE_ID:-ws-local-${short_head}}"
container_uid="${WS_DEPLOY_CONTAINER_UID:-10001}"
secret_root="${WS_DEPLOY_SECRET_ROOT:-/var/lib/worldshepherd}"
prime_dir="${secret_root}/prime-sentinel"
echo_dir="${secret_root}/echo"

prime_key="${prime_dir}/ed25519-private.pem"
prime_token_file="${prime_dir}/service-token"
echo_token_file="${echo_dir}/ingest-token"
echo_key="${echo_dir}/checkpoint-ed25519-private.pem"

as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "root privileges or sudo are required to provision UID ${container_uid} secret files"
  fi
}

as_root install -d -o "$container_uid" -g "$container_uid" -m 0700 "$prime_dir" "$echo_dir"

create_key_if_missing() {
  local target="$1"
  if as_root test -f "$target"; then
    return 0
  fi
  local temporary
  temporary="$(mktemp)"
  openssl genpkey -algorithm Ed25519 -out "$temporary" >/dev/null 2>&1
  chmod 0600 "$temporary"
  as_root install -o "$container_uid" -g "$container_uid" -m 0600 "$temporary" "$target"
  rm -f "$temporary"
}

create_token_if_missing() {
  local target="$1"
  if as_root test -f "$target"; then
    return 0
  fi
  local temporary
  temporary="$(mktemp)"
  openssl rand -hex 32 > "$temporary"
  chmod 0600 "$temporary"
  as_root install -o "$container_uid" -g "$container_uid" -m 0600 "$temporary" "$target"
  rm -f "$temporary"
}

create_key_if_missing "$prime_key"
create_token_if_missing "$prime_token_file"
create_token_if_missing "$echo_token_file"
create_key_if_missing "$echo_key"

relay_token=""
admin_token=""
if [[ -f .env ]]; then
  relay_token="$(python3 - <<'PY'
from pathlib import Path
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("SARA_RELAY_TOKEN="):
        value=line.split("=",1)[1].strip().strip("'\"")
        if value and "replace-" not in value.lower():
            print(value)
        break
PY
)"
  admin_token="$(python3 - <<'PY'
from pathlib import Path
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("SARA_ADMIN_TOKEN="):
        value=line.split("=",1)[1].strip().strip("'\"")
        if value and "replace-" not in value.lower():
            print(value)
        break
PY
)"
fi
[[ "${#relay_token}" -ge 24 ]] || relay_token="$(openssl rand -hex 32)"
[[ "${#admin_token}" -ge 24 ]] || admin_token="$(openssl rand -hex 32)"
[[ "$relay_token" != "$admin_token" ]] || admin_token="$(openssl rand -hex 32)"

export WS_DEPLOY_RELAY_TOKEN="$relay_token"
export WS_DEPLOY_ADMIN_TOKEN="$admin_token"
export WS_DEPLOY_GIT_HEAD="$git_head"
export WS_DEPLOY_RELEASE_ID_EFFECTIVE="$release_id"
export WS_DEPLOY_PRIME_KEY="$prime_key"
export WS_DEPLOY_PRIME_TOKEN_FILE="$prime_token_file"
export WS_DEPLOY_ECHO_TOKEN_FILE="$echo_token_file"
export WS_DEPLOY_ECHO_KEY="$echo_key"

python3 - <<'PY'
import os
from pathlib import Path

path = Path(".env")
existing = {}
if path.exists():
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        existing[key.strip()] = value.strip().strip("'\"")

def value(name, default):
    return existing.get(name, default) or default

settings = {
    "SARA_RELAY_TOKEN": os.environ["WS_DEPLOY_RELAY_TOKEN"],
    "SARA_ADMIN_TOKEN": os.environ["WS_DEPLOY_ADMIN_TOKEN"],
    "SARA_BIND_HOST": "127.0.0.1",
    "SARA_PORT": "9530",
    "SARA_HOST_PORT": value("SARA_HOST_PORT", "9530"),
    "SARA_DATA_DIR": "./data",
    "SARA_MODE": "docker-local-verified-full-stack",
    "SARA_LOG_LEVEL": value("SARA_LOG_LEVEL", "info"),
    "SARA_BUILD_COMMIT": os.environ["WS_DEPLOY_GIT_HEAD"],
    "SARA_RELEASE_ID": os.environ["WS_DEPLOY_RELEASE_ID_EFFECTIVE"],
    "PRIME_SENTINEL_PUBLIC_KEYS_JSON": existing.get("PRIME_SENTINEL_PUBLIC_KEYS_JSON", "{}"),
    "PRIME_SENTINEL_REVOKED_KEY_IDS": existing.get("PRIME_SENTINEL_REVOKED_KEY_IDS", ""),
    "PRIME_SENTINEL_HOST_PORT": value("PRIME_SENTINEL_HOST_PORT", "9540"),
    "PRIME_SENTINEL_SIGNING_KEY_ID": value("PRIME_SENTINEL_SIGNING_KEY_ID", "PS-LOCAL-V1"),
    "PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH": os.environ["WS_DEPLOY_PRIME_KEY"],
    "PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH": os.environ["WS_DEPLOY_PRIME_TOKEN_FILE"],
    "ECHO_HOST_PORT": value("ECHO_HOST_PORT", "9550"),
    "ECHO_CHECKPOINT_KEY_ID": value("ECHO_CHECKPOINT_KEY_ID", "ECHO-LOCAL-V1"),
    "ECHO_CHECKPOINT_SIGNER_MODE": "LOCAL_PEM",
    "ECHO_INGEST_TOKEN_HOST_PATH": os.environ["WS_DEPLOY_ECHO_TOKEN_FILE"],
    "ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH": os.environ["WS_DEPLOY_ECHO_KEY"],
}
lines = [
    "# Generated/updated by scripts/deploy_full_stack.sh.",
    "# Contains bearer credentials. Keep mode 0600 and never commit this file.",
]
for key, val in settings.items():
    if key == "PRIME_SENTINEL_PUBLIC_KEYS_JSON":
        lines.append(f"{key}='{val}'")
    else:
        lines.append(f"{key}={val}")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
path.chmod(0o600)
PY

export PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH="$prime_key"
export PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH="$prime_token_file"
export ECHO_INGEST_TOKEN_HOST_PATH="$echo_token_file"
export ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH="$echo_key"

set -a
# shellcheck disable=SC1091
source .env
set +a

docker compose config --quiet

docker compose --profile prime-sentinel up -d --build prime-sentinel

prime_url="http://127.0.0.1:${PRIME_SENTINEL_HOST_PORT:-9540}"
wait_url() {
  local url="$1"
  local label="$2"
  for attempt in $(seq 1 45); do
    if curl --fail --silent --show-error "$url" >/dev/null 2>&1; then
      return 0
    fi
    printf '%s readiness attempt %s/45...\n' "$label" "$attempt"
    sleep 2
  done
  return 1
}

if ! wait_url "${prime_url}/readyz" "PRIME SENTINEL"; then
  docker compose --profile prime-sentinel logs --no-color --tail=100 prime-sentinel >&2 || true
  fail "PRIME SENTINEL did not become ready"
fi

prime_public="$(mktemp)"
trap 'rm -f "$prime_public"' EXIT
curl --fail --silent --show-error "${prime_url}/v1/public-key" > "$prime_public"

python3 - "$prime_public" .env "${PRIME_SENTINEL_SIGNING_KEY_ID}" <<'PY'
import json
import sys
from pathlib import Path

record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
env_path = Path(sys.argv[2])
expected_key_id = sys.argv[3]
if record.get("schema") != "WS-PRIME-SENTINEL-PUBLIC-KEY-V1":
    raise SystemExit("unexpected PRIME public-key schema")
if record.get("algorithm") != "Ed25519":
    raise SystemExit("unexpected PRIME signing algorithm")
if record.get("key_id") != expected_key_id:
    raise SystemExit("PRIME public key ID does not match configured key ID")
public = record.get("public_key_b64url")
if not isinstance(public, str) or len(public) < 40:
    raise SystemExit("PRIME public key is invalid")
trust = json.dumps({expected_key_id: public}, separators=(",", ":"))
lines = env_path.read_text(encoding="utf-8").splitlines()
lines = [line for line in lines if not line.startswith("PRIME_SENTINEL_PUBLIC_KEYS_JSON=")]
lines.append("PRIME_SENTINEL_PUBLIC_KEYS_JSON='" + trust + "'")
env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
env_path.chmod(0o600)
PY

set -a
# shellcheck disable=SC1091
source .env
set +a

preflight_dir=".deployment-evidence/preflight"
mkdir -p "$preflight_dir"
chmod 0700 .deployment-evidence "$preflight_dir"
preflight_file="${preflight_dir}/${git_head}.json"
python3 -m worldshepherd_sara.deployment_preflight   --env .env   --expected-head "$git_head"   --required-uid "$container_uid"   --output "$preflight_file" >/dev/null

docker compose --profile prime-sentinel --profile echo up -d --build

sara_url="http://127.0.0.1:${SARA_HOST_PORT:-9530}"
echo_url="http://127.0.0.1:${ECHO_HOST_PORT:-9550}"

wait_url "${sara_url}/readyz" "SARA" || fail "SARA did not become ready"
wait_url "${prime_url}/readyz" "PRIME SENTINEL" || fail "PRIME SENTINEL did not remain ready"
wait_url "${echo_url}/readyz" "ECHO" || fail "ECHO did not become ready"

scripts/verify_full_stack_runtime.sh

cat <<EOF
Worldshepherd verified local full stack: DEPLOYED
Release: ${SARA_RELEASE_ID}
Commit:  ${SARA_BUILD_COMMIT}
SARA:    ${sara_url}
PRIME:   ${prime_url}
ECHO:    ${echo_url}

Boundary: localhost-only verified software deployment. This does not authorize
public exposure, controlled/CUI/classified data, HSM/KMS custody claims, or
external certification.
EOF

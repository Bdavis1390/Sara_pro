#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
cd "$HERE"

fail() {
  printf 'CHAIN_DEPLOYMENT_BLOCKED: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is required"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is required"
command -v openssl >/dev/null 2>&1 || fail "openssl is required for Engine API JWT generation"
command -v sha256sum >/dev/null 2>&1 || fail "sha256sum is required for deployment provenance"
command -v git >/dev/null 2>&1 || fail "git is required for deployment provenance"
command -v python3 >/dev/null 2>&1 || fail "python3 is required for evidence receipt generation"

[[ -f .env ]] || fail "copy .env.example to .env and replace image placeholders with verified digest-pinned images"

# Never source .env as shell code. Accept only the deployment keys defined by
# this package, each exactly once, and treat the right-hand side as data.
allowed_keys='^(BITCOIN_CORE_IMAGE|ETHEREUM_EXECUTION_IMAGE|ETHEREUM_CONSENSUS_IMAGE|BITCOIN_NETWORK|ETHEREUM_NETWORK|ETHEREUM_CHAIN_ID|BITCOIN_MAINNET_ENABLED|ETHEREUM_MAINNET_ENABLED|LIVE_BITCOIN_BROADCAST_ENABLED|ETHEREUM_VALIDATOR_ACTIVATION_ENABLED)$'
while IFS= read -r line; do
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
  key="${line%%=*}"
  [[ "$line" == *=* ]] || fail "invalid .env line without '='"
  [[ "$key" =~ $allowed_keys ]] || fail "unexpected .env key: $key"
done < .env

read_env() {
  local name="$1"
  local count value
  count="$(grep -c "^${name}=" .env || true)"
  [[ "$count" == "1" ]] || fail "$name must appear exactly once in .env"
  value="$(grep -m1 "^${name}=" .env | cut -d= -f2-)"
  [[ -n "$value" ]] || fail "$name must not be empty"
  printf '%s' "$value"
}

BITCOIN_CORE_IMAGE="$(read_env BITCOIN_CORE_IMAGE)"
ETHEREUM_EXECUTION_IMAGE="$(read_env ETHEREUM_EXECUTION_IMAGE)"
ETHEREUM_CONSENSUS_IMAGE="$(read_env ETHEREUM_CONSENSUS_IMAGE)"
BITCOIN_NETWORK="$(read_env BITCOIN_NETWORK)"
ETHEREUM_NETWORK="$(read_env ETHEREUM_NETWORK)"
ETHEREUM_CHAIN_ID="$(read_env ETHEREUM_CHAIN_ID)"
BITCOIN_MAINNET_ENABLED="$(read_env BITCOIN_MAINNET_ENABLED)"
ETHEREUM_MAINNET_ENABLED="$(read_env ETHEREUM_MAINNET_ENABLED)"
LIVE_BITCOIN_BROADCAST_ENABLED="$(read_env LIVE_BITCOIN_BROADCAST_ENABLED)"
ETHEREUM_VALIDATOR_ACTIVATION_ENABLED="$(read_env ETHEREUM_VALIDATOR_ACTIVATION_ENABLED)"
export BITCOIN_CORE_IMAGE ETHEREUM_EXECUTION_IMAGE ETHEREUM_CONSENSUS_IMAGE
export BITCOIN_NETWORK ETHEREUM_NETWORK ETHEREUM_CHAIN_ID
export BITCOIN_MAINNET_ENABLED ETHEREUM_MAINNET_ENABLED
export LIVE_BITCOIN_BROADCAST_ENABLED ETHEREUM_VALIDATOR_ACTIVATION_ENABLED

for name in BITCOIN_CORE_IMAGE ETHEREUM_EXECUTION_IMAGE ETHEREUM_CONSENSUS_IMAGE; do
  value="${!name}"
  [[ "$value" =~ @sha256:[0-9a-fA-F]{64}$ ]] || fail "$name must end in @sha256:<64 hex>"
  [[ "$value" != *replace-with* ]] || fail "$name still contains a placeholder"
done

[[ "$BITCOIN_NETWORK" == "signet" ]] || fail "BITCOIN_NETWORK must be signet"
[[ "$ETHEREUM_NETWORK" == "hoodi" ]] || fail "ETHEREUM_NETWORK must be hoodi"
[[ "$ETHEREUM_CHAIN_ID" == "560048" ]] || fail "ETHEREUM_CHAIN_ID must be 560048"
[[ "$BITCOIN_MAINNET_ENABLED" == "false" ]] || fail "Bitcoin mainnet is forbidden in this package"
[[ "$ETHEREUM_MAINNET_ENABLED" == "false" ]] || fail "Ethereum mainnet is forbidden in this package"
[[ "$LIVE_BITCOIN_BROADCAST_ENABLED" == "false" ]] || fail "Bitcoin broadcast must remain disabled"
[[ "$ETHEREUM_VALIDATOR_ACTIVATION_ENABLED" == "false" ]] || fail "Ethereum validator activation must remain disabled"

DEPLOYMENT_REVISION="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
[[ "$DEPLOYMENT_REVISION" =~ ^[0-9a-f]{40}$ ]] || fail "deployment must run from a Git checkout with a resolvable commit SHA"
COMPOSE_SHA256="$(sha256sum compose.observer.yaml | awk '{print $1}')"
export DEPLOYMENT_REVISION COMPOSE_SHA256

mkdir -p secrets artifacts
chmod 700 secrets

if [[ ! -s secrets/engine-jwt.hex ]]; then
  umask 077
  openssl rand -hex 32 > secrets/engine-jwt.hex
fi
chmod 600 secrets/engine-jwt.hex

if find . -maxdepth 2 -type f \( -iname '*wallet*' -o -iname '*keystore*' -o -iname '*mnemonic*' -o -iname '*validator-key*' \) | grep -q .; then
  fail "wallet/validator signing material must not be stored in this deployment directory"
fi

docker compose -f compose.observer.yaml config >/dev/null
docker compose -f compose.observer.yaml pull
docker compose -f compose.observer.yaml up -d

python3 - <<'PY'
import json
import os
from pathlib import Path

receipt = {
    "schema": "WS-QCRYPTO-CHAIN-START-RECEIPT-V2",
    "state": "PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED",
    "deployment_revision": os.environ["DEPLOYMENT_REVISION"],
    "compose_sha256": os.environ["COMPOSE_SHA256"],
    "images": {
        "bitcoin_core": os.environ["BITCOIN_CORE_IMAGE"],
        "ethereum_execution": os.environ["ETHEREUM_EXECUTION_IMAGE"],
        "ethereum_consensus": os.environ["ETHEREUM_CONSENSUS_IMAGE"],
    },
    "bitcoin_network": "SIGNET",
    "ethereum_network": "HOODI",
    "ethereum_chain_id": 560048,
    "claims": {
        "mainnet_permitted": False,
        "live_value_authorized": False,
        "private_key_operations_permitted": False,
        "bitcoin_transaction_broadcast": False,
        "ethereum_validator_activated": False,
        "end_to_end_post_quantum_security_established": False,
    },
    "next_verification": "python3 verify_online.py",
}
Path("artifacts/qcrypto_chain_start_receipt.json").write_text(
    json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(receipt, sort_keys=True))
PY

printf '%s\n' 'PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED'
printf '%s\n' 'Run python3 verify_online.py only after the nodes have had time to establish peers/synchronize.'

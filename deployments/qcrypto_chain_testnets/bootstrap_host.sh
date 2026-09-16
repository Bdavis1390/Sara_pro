#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

fail() {
  printf 'CHAIN_DEPLOYMENT_BLOCKED: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "docker is required"
docker compose version >/dev/null 2>&1 || fail "docker compose plugin is required"
command -v openssl >/dev/null 2>&1 || fail "openssl is required for Engine API JWT generation"

[[ -f .env ]] || fail "copy .env.example to .env and replace image placeholders with verified digest-pinned images"

# Load only the declared deployment variables for validation. Docker Compose will
# read the same .env file. Do not place wallet/validator secrets in .env.
set -a
# shellcheck disable=SC1091
source ./.env
set +a

for name in BITCOIN_CORE_IMAGE ETHEREUM_EXECUTION_IMAGE ETHEREUM_CONSENSUS_IMAGE; do
  value="${!name:-}"
  [[ "$value" =~ @sha256:[0-9a-fA-F]{64}$ ]] || fail "$name must end in @sha256:<64 hex>"
  [[ "$value" != *replace-with* ]] || fail "$name still contains a placeholder"
done

[[ "${BITCOIN_NETWORK:-}" == "signet" ]] || fail "BITCOIN_NETWORK must be signet"
[[ "${ETHEREUM_NETWORK:-}" == "hoodi" ]] || fail "ETHEREUM_NETWORK must be hoodi"
[[ "${ETHEREUM_CHAIN_ID:-}" == "560048" ]] || fail "ETHEREUM_CHAIN_ID must be 560048"
[[ "${BITCOIN_MAINNET_ENABLED:-false}" == "false" ]] || fail "Bitcoin mainnet is forbidden in this package"
[[ "${ETHEREUM_MAINNET_ENABLED:-false}" == "false" ]] || fail "Ethereum mainnet is forbidden in this package"
[[ "${LIVE_BITCOIN_BROADCAST_ENABLED:-false}" == "false" ]] || fail "Bitcoin broadcast must remain disabled"
[[ "${ETHEREUM_VALIDATOR_ACTIVATION_ENABLED:-false}" == "false" ]] || fail "Ethereum validator activation must remain disabled"

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

cat > artifacts/qcrypto_chain_start_receipt.json <<JSON
{
  "schema": "WS-QCRYPTO-CHAIN-START-RECEIPT-V1",
  "state": "PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED",
  "bitcoin_network": "SIGNET",
  "ethereum_network": "HOODI",
  "ethereum_chain_id": 560048,
  "mainnet_permitted": false,
  "live_value_authorized": false,
  "private_key_operations_permitted": false,
  "bitcoin_transaction_broadcast": false,
  "ethereum_validator_activated": false,
  "next_verification": "python3 verify_online.py"
}
JSON

printf '%s\n' 'PUBLIC_TESTNET_NODES_STARTED_SYNC_NOT_YET_ATTESTED'
printf '%s\n' 'Run python3 verify_online.py only after the nodes have had time to establish peers/synchronize.'

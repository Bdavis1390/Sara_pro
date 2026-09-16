#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
ARTIFACT_DIR="${1:-$HERE/artifacts}"
BITCOIN_VERSION="${BITCOIN_VERSION:-31.1}"
GETH_IMAGE="${GETH_IMAGE:-ethereum/client-go:v1.17.5}"
LIGHTHOUSE_IMAGE="${LIGHTHOUSE_IMAGE:-sigp/lighthouse:v8.2.2}"

fail() {
  printf 'PUBLIC_TESTNET_HANDSHAKE_FAILED: %s\n' "$*" >&2
  exit 1
}

for cmd in curl tar sha256sum gpg git docker jq openssl python3; do
  command -v "$cmd" >/dev/null 2>&1 || fail "$cmd is required"
done

[[ "$BITCOIN_VERSION" =~ ^[0-9]+\.[0-9]+$ ]] || fail "Bitcoin version must be an explicit stable release"
[[ "$GETH_IMAGE" == ethereum/client-go:v* ]] || fail "Geth image must use an explicit ethereum/client-go version tag"
[[ "$GETH_IMAGE" != *latest* ]] || fail "Geth latest tags are forbidden"
[[ "$LIGHTHOUSE_IMAGE" == sigp/lighthouse:v* ]] || fail "Lighthouse image must use an explicit sigp/lighthouse version tag"
[[ "$LIGHTHOUSE_IMAGE" != *latest* ]] || fail "Lighthouse latest tags are forbidden"

TMP="$(mktemp -d)"
BTC_DATA="$TMP/bitcoin-data"
GPG_HOME="$TMP/gnupg"
JWT="$TMP/engine-jwt.hex"
DOCKER_NETWORK="qcrypto-handshake-${GITHUB_RUN_ID:-$$}"
GETH_CONTAINER="qcrypto-geth-hoodi-${GITHUB_RUN_ID:-$$}"
LIGHTHOUSE_CONTAINER="qcrypto-lighthouse-hoodi-${GITHUB_RUN_ID:-$$}"
mkdir -p "$ARTIFACT_DIR" "$BTC_DATA" "$GPG_HOME"
chmod 700 "$GPG_HOME"

cleanup() {
  set +e
  if [[ -n "${BTC_CLI:-}" && -x "${BTC_CLI:-}" ]]; then
    "$BTC_CLI" -signet -datadir="$BTC_DATA" stop >/dev/null 2>&1 || true
  fi
  docker rm -f "$LIGHTHOUSE_CONTAINER" "$GETH_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$DOCKER_NETWORK" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT

cd "$TMP"
BTC_BASE="https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}"
BTC_ARCHIVE="bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 -O "$BTC_BASE/$BTC_ARCHIVE"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 -O "$BTC_BASE/SHA256SUMS"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 -O "$BTC_BASE/SHA256SUMS.asc"

git clone --depth 1 https://github.com/bitcoin-core/guix.sigs.git bitcoin-guix-sigs >/dev/null 2>&1
gpg --homedir "$GPG_HOME" --batch --import bitcoin-guix-sigs/builder-keys/*.gpg >/dev/null 2>&1
set +e
GPG_STATUS="$(gpg --homedir "$GPG_HOME" --batch --status-fd 1 --verify SHA256SUMS.asc SHA256SUMS 2>&1)"
GPG_RC=$?
set -e
[[ "$GPG_RC" == "0" ]] || fail "Bitcoin Core SHA256SUMS signatures did not verify"
GOOD_SIGS="$(printf '%s\n' "$GPG_STATUS" | grep -c '^\[GNUPG:\] GOODSIG ' || true)"
[[ "$GOOD_SIGS" -ge 2 ]] || fail "Bitcoin Core release requires at least two verified builder signatures"
sha256sum --ignore-missing --check SHA256SUMS | grep -F "$BTC_ARCHIVE: OK" >/dev/null || fail "Bitcoin Core archive checksum mismatch"
BTC_ARCHIVE_SHA256="$(sha256sum "$BTC_ARCHIVE" | awk '{print $1}')"
tar -xzf "$BTC_ARCHIVE"
BTC_BIN="$TMP/bitcoin-${BITCOIN_VERSION}/bin"
BTC_DAEMON="$BTC_BIN/bitcoind"
BTC_CLI="$BTC_BIN/bitcoin-cli"
[[ -x "$BTC_DAEMON" && -x "$BTC_CLI" ]] || fail "Bitcoin Core daemon/CLI missing after verified extraction"

"$BTC_DAEMON" \
  -signet \
  -datadir="$BTC_DATA" \
  -server=1 \
  -disablewallet=1 \
  -dbcache=64 \
  -maxconnections=16 \
  -daemonwait >/dev/null

BTC_PEERS=0
for _ in $(seq 1 90); do
  if BTC_NETWORK_INFO="$($BTC_CLI -signet -datadir="$BTC_DATA" getnetworkinfo 2>/dev/null)"; then
    BTC_PEERS="$(printf '%s' "$BTC_NETWORK_INFO" | jq -r '.connections // 0')"
    [[ "$BTC_PEERS" -ge 1 ]] && break
  fi
  sleep 2
done
[[ "$BTC_PEERS" -ge 1 ]] || fail "Bitcoin Signet node did not establish a peer within the bounded handshake window"
BTC_CHAIN_INFO="$($BTC_CLI -signet -datadir="$BTC_DATA" getblockchaininfo)"
[[ "$(printf '%s' "$BTC_CHAIN_INFO" | jq -r '.chain')" == "signet" ]] || fail "Bitcoin node did not report signet"
BTC_BLOCKS="$(printf '%s' "$BTC_CHAIN_INFO" | jq -r '.blocks')"
BTC_HEADERS="$(printf '%s' "$BTC_CHAIN_INFO" | jq -r '.headers')"

openssl rand -hex 32 > "$JWT"
chmod 644 "$JWT" # ephemeral CI Engine API secret; removed by trap, never used for signing

docker pull "$GETH_IMAGE" >/dev/null
docker pull "$LIGHTHOUSE_IMAGE" >/dev/null
GETH_DIGEST="$(docker image inspect --format '{{json .RepoDigests}}' "$GETH_IMAGE" | jq -r '.[0]')"
LIGHTHOUSE_DIGEST="$(docker image inspect --format '{{json .RepoDigests}}' "$LIGHTHOUSE_IMAGE" | jq -r '.[0]')"
[[ "$GETH_DIGEST" == *@sha256:* ]] || fail "Could not resolve immutable Geth image digest"
[[ "$LIGHTHOUSE_DIGEST" == *@sha256:* ]] || fail "Could not resolve immutable Lighthouse image digest"

docker network create "$DOCKER_NETWORK" >/dev/null

docker run -d \
  --name "$GETH_CONTAINER" \
  --network "$DOCKER_NETWORK" \
  -v "$JWT:/run/engine-jwt.hex:ro" \
  --entrypoint geth \
  "$GETH_IMAGE" \
  --hoodi \
  --syncmode=snap \
  --cache=256 \
  --maxpeers=20 \
  --http=false \
  --ws=false \
  --authrpc.addr=0.0.0.0 \
  --authrpc.port=8551 \
  --authrpc.jwtsecret=/run/engine-jwt.hex >/dev/null

docker run -d \
  --name "$LIGHTHOUSE_CONTAINER" \
  --network "$DOCKER_NETWORK" \
  -p 127.0.0.1:15052:5052 \
  -v "$JWT:/run/engine-jwt.hex:ro" \
  --entrypoint lighthouse \
  "$LIGHTHOUSE_IMAGE" \
  bn \
  --network hoodi \
  --execution-endpoint "http://$GETH_CONTAINER:8551" \
  --execution-jwt /run/engine-jwt.hex \
  --checkpoint-sync-url https://hoodi.checkpoint.sigp.io \
  --checkpoint-sync-url-timeout 180 \
  --disable-upnp \
  --http \
  --http-address 0.0.0.0 \
  --http-port 5052 \
  --target-peers 20 >/dev/null

GETH_PEERS=0
GETH_CHAIN_ID=""
for _ in $(seq 1 120); do
  if GETH_PEERS_RAW="$(docker exec "$GETH_CONTAINER" geth attach /root/.ethereum/geth.ipc --exec 'admin.peers.length' 2>/dev/null)"; then
    GETH_PEERS="$(printf '%s' "$GETH_PEERS_RAW" | tr -dc '0-9')"
    GETH_PEERS="${GETH_PEERS:-0}"
    GETH_CHAIN_RAW="$(docker exec "$GETH_CONTAINER" geth attach /root/.ethereum/geth.ipc --exec 'eth.chainId' 2>/dev/null || true)"
    GETH_CHAIN_ID="$(printf '%s' "$GETH_CHAIN_RAW" | tr -d '"[:space:]')"
    [[ "$GETH_PEERS" -ge 1 ]] && break
  fi
  sleep 2
done
[[ "$GETH_PEERS" -ge 1 ]] || fail "Geth Hoodi node did not establish a peer within the bounded handshake window"
python3 - "$GETH_CHAIN_ID" <<'PY'
import sys
value=sys.argv[1]
if int(value, 0) != 560048:
    raise SystemExit(f"unexpected Hoodi chain id: {value}")
PY

LIGHTHOUSE_PEERS=0
LIGHTHOUSE_SYNC_JSON=""
for _ in $(seq 1 120); do
  if PEER_JSON="$(curl --fail --silent http://127.0.0.1:15052/eth/v1/node/peer_count 2>/dev/null)"; then
    LIGHTHOUSE_PEERS="$(printf '%s' "$PEER_JSON" | jq -r '.data.connected // "0"' | tr -dc '0-9')"
    LIGHTHOUSE_PEERS="${LIGHTHOUSE_PEERS:-0}"
    LIGHTHOUSE_SYNC_JSON="$(curl --fail --silent http://127.0.0.1:15052/eth/v1/node/syncing 2>/dev/null || true)"
    [[ "$LIGHTHOUSE_PEERS" -ge 1 && -n "$LIGHTHOUSE_SYNC_JSON" ]] && break
  fi
  sleep 2
done
[[ "$LIGHTHOUSE_PEERS" -ge 1 ]] || fail "Lighthouse Hoodi node did not establish a peer within the bounded handshake window"
[[ -n "$LIGHTHOUSE_SYNC_JSON" ]] || fail "Lighthouse Hoodi sync API did not become available"

DEPLOYMENT_REVISION="$(git -C "$REPO_ROOT" rev-parse HEAD)"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export DEPLOYMENT_REVISION TIMESTAMP BITCOIN_VERSION BTC_ARCHIVE_SHA256 GOOD_SIGS BTC_PEERS BTC_BLOCKS BTC_HEADERS
export GETH_IMAGE GETH_DIGEST GETH_PEERS GETH_CHAIN_ID LIGHTHOUSE_IMAGE LIGHTHOUSE_DIGEST LIGHTHOUSE_PEERS LIGHTHOUSE_SYNC_JSON

python3 - "$ARTIFACT_DIR/qcrypto_public_testnet_handshake.json" <<'PY'
import json
import os
import sys
from pathlib import Path

sync=json.loads(os.environ["LIGHTHOUSE_SYNC_JSON"])
receipt={
    "schema":"WS-QCRYPTO-PUBLIC-TESTNET-HANDSHAKE-V1",
    "status":"LIVE_PUBLIC_TESTNET_HANDSHAKE_PASS",
    "captured_at":os.environ["TIMESTAMP"],
    "deployment_revision":os.environ["DEPLOYMENT_REVISION"],
    "bitcoin":{
        "network":"SIGNET",
        "core_version":os.environ["BITCOIN_VERSION"],
        "archive_sha256":os.environ["BTC_ARCHIVE_SHA256"],
        "verified_release_signature_count":int(os.environ["GOOD_SIGS"]),
        "connected_peers":int(os.environ["BTC_PEERS"]),
        "blocks":int(os.environ["BTC_BLOCKS"]),
        "headers":int(os.environ["BTC_HEADERS"]),
        "wallet_disabled":True,
    },
    "ethereum":{
        "network":"HOODI",
        "chain_id":560048,
        "geth_image":os.environ["GETH_IMAGE"],
        "geth_image_digest":os.environ["GETH_DIGEST"],
        "geth_connected_peers":int(os.environ["GETH_PEERS"]),
        "lighthouse_image":os.environ["LIGHTHOUSE_IMAGE"],
        "lighthouse_image_digest":os.environ["LIGHTHOUSE_DIGEST"],
        "lighthouse_connected_peers":int(os.environ["LIGHTHOUSE_PEERS"]),
        "consensus_sync":sync.get("data",{}),
        "validator_client_started":False,
    },
    "claims":{
        "mainnet_permitted":False,
        "live_value_authorized":False,
        "private_key_operations_permitted":False,
        "bitcoin_transaction_created":False,
        "bitcoin_transaction_broadcast":False,
        "ethereum_validator_activated":False,
        "end_to_end_post_quantum_security_established":False,
    },
}
Path(sys.argv[1]).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
PY

printf '%s\n' 'LIVE_PUBLIC_TESTNET_HANDSHAKE_PASS'

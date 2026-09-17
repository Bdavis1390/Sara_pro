#!/usr/bin/env bash
set -euo pipefail
umask 077

# Build the exact Bitcoin Core v32.0rc1 commit from source and execute BC32-001.
# The probe itself enforces regtest and networkactive=0 before testing.

ROOT="${BC32_WORKDIR:-${TMPDIR:-/tmp}/worldshepherd-bc32}"
SRC="$ROOT/bitcoin"
BUILD="$SRC/build"
EVIDENCE="${BC32_EVIDENCE:-$PWD/bitcoin-core-32-psbt-evidence.json}"
PINNED_TAG="v32.0rc1"
PINNED_COMMIT="d0231bb01d83178224bf7b198ba04f78cc2c89ef"
REPO="https://github.com/bitcoin/bitcoin.git"
PROBE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/external_anchor_pilots/bitcoin_core_32_psbt_probe.py"

need=(git cmake python3 c++ pkg-config)
for cmd in "${need[@]}"; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "missing required command: $cmd" >&2
    exit 2
  }
done

missing_deps=()
pkg-config --exists libevent || missing_deps+=("libevent-dev")
pkg-config --exists sqlite3 || missing_deps+=("libsqlite3-dev")
if (( ${#missing_deps[@]} > 0 )); then
  echo "missing Bitcoin Core build dependencies: ${missing_deps[*]}" >&2
  echo "On Debian/Ubuntu: sudo apt install build-essential cmake git python3 libboost-dev libevent-dev libsqlite3-dev pkg-config" >&2
  exit 2
fi

rm -rf "$ROOT"
mkdir -p "$ROOT"

git clone --filter=blob:none --no-checkout "$REPO" "$SRC"
git -C "$SRC" fetch --depth=1 origin "refs/tags/$PINNED_TAG:refs/tags/$PINNED_TAG"
git -C "$SRC" checkout --detach "$PINNED_TAG"

actual_commit="$(git -C "$SRC" rev-parse HEAD)"
if [[ "$actual_commit" != "$PINNED_COMMIT" ]]; then
  echo "source pin mismatch: expected $PINNED_COMMIT, got $actual_commit" >&2
  exit 3
fi

cmake -S "$SRC" -B "$BUILD" \
  -DBUILD_GUI=OFF \
  -DBUILD_TESTS=OFF \
  -DBUILD_BENCH=OFF \
  -DENABLE_IPC=OFF \
  -DWITH_ZMQ=OFF \
  -DWITH_USDT=OFF \
  -DCMAKE_BUILD_TYPE=Release

cmake --build "$BUILD" --target bitcoind bitcoin-cli -j "${BC32_BUILD_JOBS:-2}"

python3 "$PROBE" \
  --bitcoind "$BUILD/bin/bitcoind" \
  --bitcoin-cli "$BUILD/bin/bitcoin-cli" \
  --expected-version-substring "v32.0.0rc1" \
  --prime-gate-id "${BC32_PRIME_GATE_ID:-UNSET}" \
  --operator "${BC32_OPERATOR:-${GITHUB_ACTOR:-UNRECORDED}}" \
  --evidence "$EVIDENCE"

echo "BC32-001 evidence: $EVIDENCE"

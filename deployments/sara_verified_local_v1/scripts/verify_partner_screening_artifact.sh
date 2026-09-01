#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE' >&2
Usage:
  verify_partner_screening_artifact.sh <partner-screening-batch.zip|extracted-package-dir> [expected-artifact-sha256]

Purpose:
  Verify a downloaded or extracted Worldshepherd partner-screening artifact before review or sharing.

Inputs:
  <partner-screening-batch.zip|extracted-package-dir>
      A GitHub Actions artifact ZIP, an extracted batch directory containing batch-manifest.json,
      or one partner package directory containing manifest.json.

  [expected-artifact-sha256]
      Optional SHA-256 digest for the ZIP. Accepts either '<hex>' or 'sha256:<hex>'.
      Use this with the digest shown by GitHub Actions for the downloaded artifact.

Claims boundary:
  This script verifies file integrity and manifest consistency only. It does not establish partner
  validation, supplier approval, certification, CMMC/NIST/DFARS conformity, classified access,
  external reproduction, field performance, hardware performance, or operational authority.
USAGE
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

INPUT=$1
EXPECTED_DIGEST=${2:-}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
TMP_DIR=""

cleanup() {
  if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

normalize_digest() {
  local value=$1
  value=${value#sha256:}
  printf '%s' "$value"
}

resolve_artifact_root() {
  local root=$1

  if [[ -f "$root/batch-manifest.json" || -f "$root/manifest.json" ]]; then
    printf '%s' "$root"
    return 0
  fi

  if [[ -d "$root/partner_screening_ci" ]]; then
    if [[ -f "$root/partner_screening_ci/batch-manifest.json" || -f "$root/partner_screening_ci/manifest.json" ]]; then
      printf '%s' "$root/partner_screening_ci"
      return 0
    fi
  fi

  mapfile -t candidates < <(find "$root" -maxdepth 3 \( -name batch-manifest.json -o -name manifest.json \) -type f | sort)
  if [[ ${#candidates[@]} -eq 1 ]]; then
    dirname "${candidates[0]}"
    return 0
  fi

  fail "could not resolve a unique partner-screening manifest under $root"
}

if [[ -f "$INPUT" ]]; then
  INPUT_ABS=$(cd "$(dirname "$INPUT")" && pwd -P)/$(basename "$INPUT")
  case "$INPUT_ABS" in
    *.zip) ;;
    *) fail "file input must be a .zip artifact: $INPUT_ABS" ;;
  esac

  if [[ -n "$EXPECTED_DIGEST" ]]; then
    command -v sha256sum >/dev/null || fail "sha256sum is required to compare the artifact ZIP digest"
    EXPECTED_HEX=$(normalize_digest "$EXPECTED_DIGEST")
    ACTUAL_HEX=$(sha256sum "$INPUT_ABS" | awk '{print $1}')
    if [[ "$ACTUAL_HEX" != "$EXPECTED_HEX" ]]; then
      fail "artifact ZIP digest mismatch: expected sha256:$EXPECTED_HEX, got sha256:$ACTUAL_HEX"
    fi
  fi

  command -v unzip >/dev/null || fail "unzip is required to inspect artifact ZIP files"
  TMP_DIR=$(mktemp -d)
  unzip -q "$INPUT_ABS" -d "$TMP_DIR"
  ARTIFACT_ROOT=$(resolve_artifact_root "$TMP_DIR")
elif [[ -d "$INPUT" ]]; then
  ARTIFACT_ROOT=$(cd "$INPUT" && pwd -P)
  ARTIFACT_ROOT=$(resolve_artifact_root "$ARTIFACT_ROOT")
else
  fail "input does not exist: $INPUT"
fi

if [[ -f "$ARTIFACT_ROOT/batch-manifest.json" ]]; then
  MODE="--batch"
elif [[ -f "$ARTIFACT_ROOT/manifest.json" ]]; then
  MODE="--package"
else
  fail "resolved artifact root has neither batch-manifest.json nor manifest.json: $ARTIFACT_ROOT"
fi

if command -v ws-partner-screening-verify >/dev/null; then
  ws-partner-screening-verify "$MODE" "$ARTIFACT_ROOT"
else
  (cd "$PROJECT_ROOT" && python -m worldshepherd_sara.partner_screening_verify_cli "$MODE" "$ARTIFACT_ROOT")
fi

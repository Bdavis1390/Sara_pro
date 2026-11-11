#!/usr/bin/env bash
# WorldShepherd: bounded, audit-only Modern Web Guidance scanner.
# Run with: bash scripts/mwg_readonly_audit.sh /absolute/path/to/frontend
set -euo pipefail
umask 077
export DISABLE_TELEMETRY=1

if [[ "$#" -ne 1 ]]; then
  printf 'Usage: bash %s /absolute/path/to/frontend\n' "$0" >&2
  exit 2
fi

for command_name in realpath node npx timeout nice; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command_name" >&2
    exit 2
  fi
done

target="$(realpath -e -- "$1")"
if [[ ! -d "$target" ]]; then
  printf 'Target is not a directory: %s\n' "$target" >&2
  exit 2
fi

# Never accidentally scan an entire system or operator home.
case "$target" in
  /|/home|/tmp|"$HOME")
    printf 'Refusing broad scan root: %s\n' "$target" >&2
    exit 2
    ;;
esac

# The scanner runs locally and does not edit target code. npm/npx may
# populate the per-user package cache. Reports are outside the codebase.
report_dir="${XDG_STATE_HOME:-$HOME/.local/state}/worldshepherd/mwg/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p -- "$report_dir"
package="${MWG_PACKAGE:-modern-web-guidance@latest}"

{
  printf 'project=%s\n' "$target"
  printf 'utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'node=%s\n' "$(node --version)"
  printf 'package=%s\n' "$package"
  printf 'telemetry=disabled\n'
  printf 'mode=read-only\n'
} >"$report_dir/manifest.txt"

if ! timeout 60s npx --yes "$package" --version >"$report_dir/cli-version.txt" 2>"$report_dir/version-stderr.txt"; then
  printf 'Could not verify CLI version. See %s\n' "$report_dir" >&2
  exit 1
fi

set +e
nice -n 10 timeout 180s npx --yes "$package" legacy-scan "$target" --json \
  >"$report_dir/legacy-scan.json" 2>"$report_dir/legacy-scan-stderr.txt"
exit_code=$?
set -e

printf 'scan_exit_code=%s\n' "$exit_code" >>"$report_dir/manifest.txt"
printf 'Audit report: %s\n' "$report_dir"
printf 'No source files were modified by this wrapper.\n'
exit "$exit_code"

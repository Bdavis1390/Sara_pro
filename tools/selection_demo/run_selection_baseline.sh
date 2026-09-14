#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEPLOY="$REPO_ROOT/deployments/sara_verified_local_v1"
MANIFEST="$REPO_ROOT/config/worldshepherd_selection_test_manifest_v0_1.json"
OUT="${WS_SELECTION_EVIDENCE_DIR:-$REPO_ROOT/selection_evidence}"
SOURCE_SHA="${GITHUB_SHA:-$(git -C "$REPO_ROOT" rev-parse HEAD)}"
EXECUTED_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "$OUT"
rm -rf "$OUT/tests" "$OUT/qualification_evidence" "$OUT/operational_resilience_evidence"
mkdir -p "$OUT/tests"

for cmd in python git docker curl openssl ws-pre-bloom pytest; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "missing required command: $cmd" >&2; exit 2; }
done

test -f "$MANIFEST" || { echo "missing selection manifest: $MANIFEST" >&2; exit 2; }

mapfile -t SELECTION_TESTS < <(python - "$MANIFEST" <<'PY'
import json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
for path in manifest.get('selection_core_tests', []):
    print(path)
PY
)

if (( ${#SELECTION_TESTS[@]} == 0 )); then
  echo "selection manifest contains no core tests" >&2
  exit 2
fi

printf '[selection] exact commit: %s\n' "$SOURCE_SHA"
printf '[selection] selection-core tests: %d files\n' "${#SELECTION_TESTS[@]}"
(
  cd "$DEPLOY"
  pytest -q "${SELECTION_TESTS[@]}" | tee "$OUT/tests/selection-core-pytest.txt"
)

printf '[selection] retained negative-evidence research check: NSB G10\n'
set +e
(
  cd "$DEPLOY"
  pytest -q tests/test_nsb_g10_nonlinear_mhd.py >"$OUT/tests/research-g10-pytest.txt" 2>&1
)
G10_EXIT=$?
set -e
printf '%s\n' "$G10_EXIT" > "$OUT/tests/research-g10-exit-code.txt"
if (( G10_EXIT == 0 )); then
  G10_STATUS="PASS"
else
  G10_STATUS="KNOWN_FAILURE_RETAINED"
fi
printf '[selection] G10 research status: %s\n' "$G10_STATUS"

printf '[selection] PRE qualification/evidence compiler\n'
(
  cd "$DEPLOY"
  ws-pre-bloom \
    --fixtures fixtures \
    --out "$OUT/qualification_evidence" \
    --software-commit "$SOURCE_SHA" \
    --executed-utc "$EXECUTED_UTC" \
    --operator "selection-baseline"
)

printf '[selection] operational resilience drill\n'
OPS_RESILIENCE_EVIDENCE_DIR="$OUT/operational_resilience_evidence" \
  "$DEPLOY/scripts/operational_resilience_drill.sh"

export REPO_ROOT OUT SOURCE_SHA EXECUTED_UTC MANIFEST G10_STATUS
python - <<'PY'
import hashlib, json, os, pathlib
root = pathlib.Path(os.environ['REPO_ROOT'])
out = pathlib.Path(os.environ['OUT'])
manifest_path = pathlib.Path(os.environ['MANIFEST'])
manifest = json.loads(manifest_path.read_text())

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(path.read_text())

resilience_path = out/'operational_resilience_evidence'/'operational-resilience-evidence.json'
resilience = load_json(resilience_path) if resilience_path.exists() else {'result': 'MISSING'}
qualification_index = out/'qualification_evidence'/'qualification_index.json'
qualification = load_json(qualification_index) if qualification_index.exists() else None
license_names = ['LICENSE','LICENSE.md','LICENSE.txt','COPYING','COPYING.md','COPYING.txt']
license_present = any((root/name).is_file() for name in license_names)
security_boundary_present = (root/'SECURITY.md').is_file()
selection_matrix_present = (root/'config/worldshepherd_preferred_choice_matrix_v0_1.json').is_file()
selection_manifest_present = manifest_path.is_file()

artifacts = []
for p in sorted(out.rglob('*')):
    if p.is_file() and p.name != 'selection-baseline.json':
        artifacts.append({'path': str(p.relative_to(out)), 'sha256': sha256(p), 'bytes': p.stat().st_size})

checks = {
    'selection_core_pytest_executed': (out/'tests/selection-core-pytest.txt').is_file(),
    'qualification_index_present': qualification is not None,
    'operational_resilience_pass': resilience.get('result') == 'PASS',
    'public_repository_security_boundary_present': security_boundary_present,
    'preferred_choice_matrix_present': selection_matrix_present,
    'selection_test_manifest_present': selection_manifest_present,
    'open_source_license_present': license_present,
}

hard_unresolved = [
    'operational_scale_performance_not_yet_benchmarked_for_DIU_PROJ00716',
    'controlled_environment_CMMC_NIST_SPRS_clearance_not_established_by_public_repo',
    'external_reference_or_partner_validation_not_yet_evidenced',
]
if not license_present:
    hard_unresolved.append('commercial_open_source_license_not_established')

research_negative_evidence = {
    'nsb_g10_nonlinear_mhd': {
        'status': os.environ['G10_STATUS'],
        'selection_core_blocking': False,
        'capability_status': 'SIMULATED_ONLY',
        'manifest_record': manifest.get('known_negative_evidence', {}).get('tests/test_nsb_g10_nonlinear_mhd.py'),
        'artifact': 'tests/research-g10-pytest.txt',
    }
}

blocking_checks = {k: v for k, v in checks.items() if k != 'open_source_license_present'}
result = 'BASELINE_PASS_WITH_UNRESOLVED_GATES' if all(blocking_checks.values()) else 'BASELINE_FAIL'
record = {
    'schema': 'WS-PREFERRED-CHOICE-SELECTION-BASELINE-V2',
    'result': result,
    'evidence_status': 'INTERNAL_REPRODUCIBLE_EVIDENCE_ONLY',
    'source_commit': os.environ['SOURCE_SHA'],
    'executed_utc': os.environ['EXECUTED_UTC'],
    'selection_core_test_count': len(manifest.get('selection_core_tests', [])),
    'checks': checks,
    'hard_unresolved_gates': hard_unresolved,
    'retained_research_negative_evidence': research_negative_evidence,
    'claims_boundary': 'Passing this baseline supports only the scoped selection-core software/governance evidence. It does not establish that unrelated research/physics suites pass, preferred vendor status, contract selection, open-source licensing, operational-scale performance, CMMC/NIST/SPRS status, clearance, ATO, or authorization to process controlled information.',
    'artifacts': artifacts,
}
(out/'selection-baseline.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
print(json.dumps(record, indent=2, sort_keys=True))
if result == 'BASELINE_FAIL':
    raise SystemExit(1)
PY

printf '\nSELECTION BASELINE COMPLETE: %s\n' "$OUT/selection-baseline.json"

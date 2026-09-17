#!/usr/bin/env bash
set -euo pipefail

# Portable reproduction harness for the bounded Worldshepherd SPDX 3.0.1 evidence.
# A successful local run proves only that this environment reproduced the exact
# controls encoded here. It does not establish independent review by itself.

EXPECTED_SCHEMA_SHA256='582c64e809d5b3ef9bd0c4de13a32391b47b0284a3e8d199569fb96f649234b1'
EXPECTED_MODEL_SHA256='30ebb4af2d70a9809044ef46f44cc3dc5125226d70f818a50ed2e1d5f404c593'
SPDX3_VALIDATE_VERSION='0.0.7'
PYSHACL_VERSION='0.40.1'
AJV_CLI_VERSION='5.0.0'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$ROOT_DIR/deployments/sara_verified_local_v1/tests/fixtures/spdx301_minimal.spdx3.json"
OUTPUT_DIR="${SPDX_REPRO_OUTPUT_DIR:-$ROOT_DIR/spdx_reproduction_evidence}"
RESOURCE_DIR="${SPDX_REPRO_RESOURCE_DIR:-}"
BOOTSTRAP="${SPDX_REPRO_BOOTSTRAP:-1}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$OUTPUT_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "required command missing: $1" >&2
    exit 2
  fi
}

require_command python3
require_command sha256sum
require_command git

if [ ! -f "$FIXTURE" ]; then
  echo "baseline fixture missing: $FIXTURE" >&2
  exit 2
fi

SCHEMA="$WORK_DIR/spdx-3.0.1-schema.json"
MODEL="$WORK_DIR/spdx-3.0.1-model.ttl"

if [ -n "$RESOURCE_DIR" ]; then
  cp "$RESOURCE_DIR/spdx-3.0.1-schema.json" "$SCHEMA"
  cp "$RESOURCE_DIR/spdx-3.0.1-model.ttl" "$MODEL"
else
  require_command curl
  curl --fail --silent --show-error --location \
    'https://spdx.org/schema/3.0.1/spdx-json-schema.json' \
    --output "$SCHEMA"
  curl --fail --silent --show-error --location \
    'https://spdx.org/rdf/3.0.1/spdx-model.ttl' \
    --output "$MODEL"
fi

test -s "$SCHEMA"
test -s "$MODEL"

schema_sha="$(sha256sum "$SCHEMA" | awk '{print $1}')"
model_sha="$(sha256sum "$MODEL" | awk '{print $1}')"
if [ "$schema_sha" != "$EXPECTED_SCHEMA_SHA256" ]; then
  echo "canonical schema digest mismatch: $schema_sha" >&2
  exit 3
fi
if [ "$model_sha" != "$EXPECTED_MODEL_SHA256" ]; then
  echo "canonical model digest mismatch: $model_sha" >&2
  exit 3
fi

if [ "$BOOTSTRAP" = '1' ]; then
  require_command npm
  python3 -m venv "$WORK_DIR/validator-venv"
  "$WORK_DIR/validator-venv/bin/python" -m pip install --disable-pip-version-check \
    "spdx3-validate==$SPDX3_VALIDATE_VERSION" \
    "pyshacl==$PYSHACL_VERSION" >/dev/null
  "$WORK_DIR/validator-venv/bin/python" -m pip check >/dev/null
  mkdir -p "$WORK_DIR/ajv"
  npm install --prefix "$WORK_DIR/ajv" --no-save "ajv-cli@$AJV_CLI_VERSION" >/dev/null
  SPDX3_VALIDATE="$WORK_DIR/validator-venv/bin/spdx3-validate"
  PYSHACL="$WORK_DIR/validator-venv/bin/pyshacl"
  AJV="$WORK_DIR/ajv/node_modules/.bin/ajv"
  VALIDATOR_PYTHON="$WORK_DIR/validator-venv/bin/python"
  AJV_ROOT="$WORK_DIR/ajv"
else
  : "${SPDX3_VALIDATE:?set SPDX3_VALIDATE when SPDX_REPRO_BOOTSTRAP=0}"
  : "${PYSHACL:?set PYSHACL when SPDX_REPRO_BOOTSTRAP=0}"
  : "${AJV:?set AJV when SPDX_REPRO_BOOTSTRAP=0}"
  : "${VALIDATOR_PYTHON:?set VALIDATOR_PYTHON to the validator Python environment when SPDX_REPRO_BOOTSTRAP=0}"
  : "${AJV_ROOT:?set AJV_ROOT to the npm prefix containing node_modules/ajv-cli when SPDX_REPRO_BOOTSTRAP=0}"
fi

for executable in "$SPDX3_VALIDATE" "$PYSHACL" "$AJV" "$VALIDATOR_PYTHON"; do
  if [ ! -x "$executable" ]; then
    echo "validator executable missing/not executable: $executable" >&2
    exit 2
  fi
done

AJV_PACKAGE_JSON="$AJV_ROOT/node_modules/ajv-cli/package.json"
if [ ! -f "$AJV_PACKAGE_JSON" ]; then
  echo "AJV package metadata missing: $AJV_PACKAGE_JSON" >&2
  exit 2
fi

spdx_version="$($VALIDATOR_PYTHON - <<'PY'
from importlib.metadata import version
print(version('spdx3-validate'))
PY
)"
pyshacl_version="$($VALIDATOR_PYTHON - <<'PY'
from importlib.metadata import version
print(version('pyshacl'))
PY
)"
ajv_version="$(python3 - "$AJV_PACKAGE_JSON" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))['version'])
PY
)"

if [ "$spdx_version" != "$SPDX3_VALIDATE_VERSION" ]; then
  echo "spdx3-validate version mismatch: expected $SPDX3_VALIDATE_VERSION, got $spdx_version" >&2
  exit 6
fi
if [ "$pyshacl_version" != "$PYSHACL_VERSION" ]; then
  echo "pySHACL version mismatch: expected $PYSHACL_VERSION, got $pyshacl_version" >&2
  exit 6
fi
if [ "$ajv_version" != "$AJV_CLI_VERSION" ]; then
  echo "ajv-cli version mismatch: expected $AJV_CLI_VERSION, got $ajv_version" >&2
  exit 6
fi

# Capture the resolved dependency graph used by this run. These manifests are
# provenance evidence, not a claim that transitive dependencies are lockfile-pinned.
"$VALIDATOR_PYTHON" -m pip freeze --all | LC_ALL=C sort > "$OUTPUT_DIR/python-validator-freeze.txt"
npm list --prefix "$AJV_ROOT" --all --json > "$OUTPUT_DIR/ajv-npm-tree.json"

BASELINE_AJV_LOG="$OUTPUT_DIR/baseline-ajv.log"
BASELINE_SHACL_LOG="$OUTPUT_DIR/baseline-pyshacl.log"
BASELINE_COMBINED_LOG="$OUTPUT_DIR/baseline-spdx3-validate.log"
STRUCTURAL_AJV_LOG="$OUTPUT_DIR/structural-negative-ajv.log"
STRUCTURAL_COMBINED_LOG="$OUTPUT_DIR/structural-negative-spdx3-validate.log"
SEMANTIC_AJV_LOG="$OUTPUT_DIR/semantic-negative-ajv.log"
SEMANTIC_SHACL_LOG="$OUTPUT_DIR/semantic-negative-pyshacl.log"
SEMANTIC_COMBINED_LOG="$OUTPUT_DIR/semantic-negative-spdx3-validate.log"

# Positive baseline.
"$AJV" validate --spec=draft2020 -s "$SCHEMA" -d "$FIXTURE" >"$BASELINE_AJV_LOG" 2>&1
"$PYSHACL" -f human -df json-ld --shacl "$MODEL" --ont-graph "$MODEL" "$FIXTURE" >"$BASELINE_SHACL_LOG" 2>&1
"$SPDX3_VALIDATE" --json "$FIXTURE" >"$BASELINE_COMBINED_LOG" 2>&1

grep -q 'Conforms: True' "$BASELINE_SHACL_LOG"

# Build both negative controls deterministically.
python3 - "$FIXTURE" "$WORK_DIR" <<'PY'
import json
import sys
from pathlib import Path

fixture = Path(sys.argv[1])
work = Path(sys.argv[2])
base = json.loads(fixture.read_text(encoding='utf-8'))

structural = json.loads(json.dumps(base))
for element in structural['@graph']:
    if element.get('type') == 'SpdxDocument':
        element['profileConformance'] = 'core'
        break
(work / 'structural-invalid.spdx3.json').write_text(
    json.dumps(structural, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)

semantic = json.loads(json.dumps(base))
package_id = next(
    element['spdxId'] for element in semantic['@graph']
    if element.get('type') == 'software_Package'
)
creation_info = next(
    element for element in semantic['@graph']
    if element.get('type') == 'CreationInfo'
)
creation_info['createdBy'] = [package_id]
(work / 'semantic-invalid.spdx3.json').write_text(
    json.dumps(semantic, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

STRUCTURAL_MUTATION="$WORK_DIR/structural-invalid.spdx3.json"
SEMANTIC_MUTATION="$WORK_DIR/semantic-invalid.spdx3.json"
cp "$STRUCTURAL_MUTATION" "$OUTPUT_DIR/structural-invalid-control.spdx3.json"
cp "$SEMANTIC_MUTATION" "$OUTPUT_DIR/semantic-invalid-control.spdx3.json"

# Structural negative: distinct structural validators must reject.
set +e
"$AJV" validate --spec=draft2020 -s "$SCHEMA" -d "$STRUCTURAL_MUTATION" >"$STRUCTURAL_AJV_LOG" 2>&1
structural_ajv_status=$?
"$SPDX3_VALIDATE" --json "$STRUCTURAL_MUTATION" >"$STRUCTURAL_COMBINED_LOG" 2>&1
structural_combined_status=$?
set -e
if [ "$structural_ajv_status" -eq 0 ] || [ "$structural_combined_status" -eq 0 ]; then
  echo 'structural negative control was unexpectedly accepted' >&2
  exit 4
fi

# Semantic negative: JSON Schema must accept, SHACL must reject.
"$AJV" validate --spec=draft2020 -s "$SCHEMA" -d "$SEMANTIC_MUTATION" >"$SEMANTIC_AJV_LOG" 2>&1
set +e
"$PYSHACL" -f human -df json-ld --shacl "$MODEL" --ont-graph "$MODEL" "$SEMANTIC_MUTATION" >"$SEMANTIC_SHACL_LOG" 2>&1
semantic_shacl_status=$?
"$SPDX3_VALIDATE" --json "$SEMANTIC_MUTATION" >"$SEMANTIC_COMBINED_LOG" 2>&1
semantic_combined_status=$?
set -e
if [ "$semantic_shacl_status" -ne 1 ]; then
  echo "semantic negative control expected pySHACL status 1, got $semantic_shacl_status" >&2
  exit 5
fi
if [ "$semantic_combined_status" -eq 0 ]; then
  echo 'combined validator unexpectedly accepted semantic negative control' >&2
  exit 5
fi
grep -q 'Conforms: False' "$SEMANTIC_SHACL_LOG"
grep -q 'Value does not have class' "$SEMANTIC_SHACL_LOG"

fixture_sha="$(sha256sum "$FIXTURE" | awk '{print $1}')"
structural_sha="$(sha256sum "$STRUCTURAL_MUTATION" | awk '{print $1}')"
semantic_sha="$(sha256sum "$SEMANTIC_MUTATION" | awk '{print $1}')"
python_manifest_sha="$(sha256sum "$OUTPUT_DIR/python-validator-freeze.txt" | awk '{print $1}')"
npm_manifest_sha="$(sha256sum "$OUTPUT_DIR/ajv-npm-tree.json" | awk '{print $1}')"
repo_head="$(git -C "$ROOT_DIR" rev-parse HEAD 2>/dev/null || printf 'UNAVAILABLE')"
python_version="$(python3 --version 2>&1)"
node_version="$(node --version 2>/dev/null || printf 'UNAVAILABLE')"

export RECEIPT_REPO_HEAD="$repo_head"
export RECEIPT_FIXTURE_SHA="$fixture_sha"
export RECEIPT_STRUCTURAL_SHA="$structural_sha"
export RECEIPT_SEMANTIC_SHA="$semantic_sha"
export RECEIPT_SCHEMA_SHA="$schema_sha"
export RECEIPT_MODEL_SHA="$model_sha"
export RECEIPT_PYTHON_MANIFEST_SHA="$python_manifest_sha"
export RECEIPT_NPM_MANIFEST_SHA="$npm_manifest_sha"
export RECEIPT_PYTHON_VERSION="$python_version"
export RECEIPT_NODE_VERSION="$node_version"
export RECEIPT_SPDX_VERSION="$spdx_version"
export RECEIPT_PYSHACL_VERSION="$pyshacl_version"
export RECEIPT_AJV_VERSION="$ajv_version"
export RECEIPT_BOOTSTRAP="$BOOTSTRAP"
export RECEIPT_OUTPUT="$OUTPUT_DIR/reproduction-receipt.json"

python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

receipt = {
    'schema': 'WS-SPDX-REPRODUCTION-RECEIPT-V1',
    'executed_at_utc': datetime.now(timezone.utc).isoformat(),
    'repository_head': os.environ['RECEIPT_REPO_HEAD'],
    'spdx_version': '3.0.1',
    'bootstrap_mode': os.environ['RECEIPT_BOOTSTRAP'] == '1',
    'resources': {
        'json_schema_sha256': 'sha256:' + os.environ['RECEIPT_SCHEMA_SHA'],
        'ontology_shacl_sha256': 'sha256:' + os.environ['RECEIPT_MODEL_SHA'],
    },
    'inputs': {
        'baseline_fixture_sha256': 'sha256:' + os.environ['RECEIPT_FIXTURE_SHA'],
        'structural_negative_sha256': 'sha256:' + os.environ['RECEIPT_STRUCTURAL_SHA'],
        'semantic_negative_sha256': 'sha256:' + os.environ['RECEIPT_SEMANTIC_SHA'],
    },
    'environment': {
        'python': os.environ['RECEIPT_PYTHON_VERSION'],
        'node': os.environ['RECEIPT_NODE_VERSION'],
        'spdx3_validate': os.environ['RECEIPT_SPDX_VERSION'],
        'pyshacl': os.environ['RECEIPT_PYSHACL_VERSION'],
        'ajv_cli': os.environ['RECEIPT_AJV_VERSION'],
        'python_dependency_manifest_sha256': 'sha256:' + os.environ['RECEIPT_PYTHON_MANIFEST_SHA'],
        'npm_dependency_manifest_sha256': 'sha256:' + os.environ['RECEIPT_NPM_MANIFEST_SHA'],
        'transitive_dependencies_lockfile_pinned': False,
    },
    'results': {
        'baseline_structural': 'PASS',
        'baseline_semantic': 'PASS',
        'baseline_combined': 'PASS',
        'structural_negative_ajv': 'REJECTED',
        'structural_negative_combined': 'REJECTED',
        'semantic_negative_ajv': 'PASS',
        'semantic_negative_pyshacl': 'REJECTED_NONCONFORMANT',
        'semantic_negative_combined': 'REJECTED',
    },
    'evidence_state': 'REPRODUCTION_PACKAGE_EXECUTED',
    'independently_reproduced': False,
    'reviewer_identity_established': False,
    'general_spdx_conformance_established': False,
    'community_endorsement_established': False,
    'supply_chain_reproducibility_established': False,
    'admission_authorized': False,
    'release_approved': False,
    'claims_boundary': (
        'A successful execution proves that this environment reproduced the exact bounded controls. '
        'Resolved dependency manifests are captured for provenance, but transitive dependencies are not '
        'lockfile-pinned. This does not establish supply-chain reproducibility or independent external '
        'reproduction until an attributable outside reviewer runs the package and supplies their own evidence.'
    ),
}
Path(os.environ['RECEIPT_OUTPUT']).write_text(
    json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8'
)
PY

python3 -m json.tool "$OUTPUT_DIR/reproduction-receipt.json" >/dev/null
grep -q '"evidence_state": "REPRODUCTION_PACKAGE_EXECUTED"' "$OUTPUT_DIR/reproduction-receipt.json"
grep -q '"independently_reproduced": false' "$OUTPUT_DIR/reproduction-receipt.json"
grep -q '"supply_chain_reproducibility_established": false' "$OUTPUT_DIR/reproduction-receipt.json"

echo "SPDX reproduction package completed: $OUTPUT_DIR/reproduction-receipt.json"

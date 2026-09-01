#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-}"
if [[ -z "$ROOT" ]]; then
  echo "usage: $0 <intake-minimum-artifact-dir>" >&2
  exit 2
fi

if [[ ! -d "$ROOT" ]]; then
  echo "intake minimum artifact directory missing: $ROOT" >&2
  exit 1
fi

test -s "$ROOT/intake-minimum-ledger.json"
test -s "$ROOT/intake-minimum-summary.json"

python - "$ROOT" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
ledger = json.loads((root / "intake-minimum-ledger.json").read_text(encoding="utf-8"))
summary = json.loads((root / "intake-minimum-summary.json").read_text(encoding="utf-8"))

assert ledger["schema"] == "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1"
assert summary["schema"] == "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1"
assert summary["evidence_status"] == "INTERNAL_INTAKE_STANDARD_UNSIGNED"
assert summary["intake_count"] > 0
assert summary["intake_minimum_ledger_sha256"].startswith("sha256:")
assert summary["intake_minimum_ledger_file_sha256"].startswith("sha256:")
assert "does not establish" in summary["claims_boundary"]
assert "award probability" in summary["claims_boundary"]
for record in ledger["records"]:
    assert record["minimum_controls"]["source_custody"] == "PASS"
    assert record["minimum_controls"]["source_hash"] == "PASS"
    assert record["minimum_controls"]["claims_boundary"] == "PASS"
    assert record["minimum_controls"]["human_review_status"] == "PASS"
    assert record["minimum_controls"]["routing_status"] == "PASS"
    assert record["minimum_controls"]["downstream_route_or_evidence"] == "PASS"
    assert record["minimum_controls"]["false_claim_guard"] == "PASS"
    assert record["record_digest"].startswith("sha256:")
text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file())
for forbidden in (
    "BAE_VALIDATED",
    "PARTNER_VALIDATED",
    "SUPPLIER_APPROVED",
    "CMMC_CERTIFIED",
    "NIST_800_171_CONFORMANT",
    "VULNERABILITY_REMEDIATED",
    "OPERATIONAL_AUTHORITY_GRANTED",
):
    assert forbidden not in text
PY

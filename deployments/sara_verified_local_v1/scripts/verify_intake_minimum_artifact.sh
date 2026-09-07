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
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
ledger_path = root / "intake-minimum-ledger.json"
summary_path = root / "intake-minimum-summary.json"
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
summary = json.loads(summary_path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def canonical_digest(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


require(ledger.get("schema") == "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1", "unexpected ledger schema")
require(summary.get("schema") == "WS-INTAKE-MINIMUM-STANDARD-LEDGER-V1", "unexpected summary schema")
require(summary.get("evidence_status") == "INTERNAL_INTAKE_STANDARD_UNSIGNED", "unexpected evidence status")
records = ledger.get("records")
require(isinstance(records, list) and records, "ledger must contain records")
require(summary.get("intake_count") == len(records), "summary intake_count mismatch")
require(ledger.get("summary", {}).get("intake_count") == len(records), "ledger intake_count mismatch")

actual_file_digest = "sha256:" + hashlib.sha256(ledger_path.read_bytes()).hexdigest()
require(
    summary.get("intake_minimum_ledger_file_sha256") == actual_file_digest,
    "intake minimum ledger file digest mismatch",
)
ledger_input = dict(ledger)
recorded_ledger_digest = ledger_input.pop("ledger_digest", None)
actual_ledger_digest = canonical_digest(ledger_input)
require(recorded_ledger_digest == actual_ledger_digest, "intake minimum canonical ledger digest mismatch")
require(
    summary.get("intake_minimum_ledger_sha256") == actual_ledger_digest,
    "intake minimum summary canonical ledger digest mismatch",
)
for field in (
    "pending_human_review_count",
    "reviewed_action_required_count",
    "not_material_count",
    "review_counts",
    "routing_counts",
):
    require(summary.get(field) == ledger["summary"].get(field), f"summary {field} mismatch")

require("does not establish" in summary.get("claims_boundary", ""), "summary claims boundary missing")
require("award probability" in summary.get("claims_boundary", ""), "summary award-probability boundary missing")
for record in ledger["records"]:
    require(isinstance(record, dict), "ledger record must be an object")
    record_input = dict(record)
    recorded_record_digest = record_input.pop("record_digest", None)
    require(recorded_record_digest == canonical_digest(record_input), "intake minimum record digest mismatch")
    controls = record.get("minimum_controls", {})
    for control in (
        "source_custody",
        "source_hash",
        "claims_boundary",
        "human_review_status",
        "routing_status",
        "downstream_route_or_evidence",
        "false_claim_guard",
    ):
        require(controls.get(control) == "PASS", f"minimum control failed: {control}")
text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file())
normalized_text = text.upper()
for forbidden in (
    "BAE_VALIDATED",
    "PARTNER_VALIDATED",
    "SUPPLIER_APPROVED",
    "CMMC_CERTIFIED",
    "NIST_800_171_CONFORMANT",
    "VULNERABILITY_REMEDIATED",
    "OPERATIONAL_AUTHORITY_GRANTED",
):
    require(forbidden not in normalized_text, f"prohibited assertion present: {forbidden}")
PY

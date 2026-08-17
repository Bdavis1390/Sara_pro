#!/usr/bin/env python3
"""Validate a local external-evidence batch against the current QRF campaign gate.

Input manifest shape:
{
  "completed_preconditions": ["optional-precondition-id"],
  "evidence": [
    {
      "record": { ... ExternalEvidenceRecord fields ... },
      "artifact_bindings": [
        {"field_path": "raw_artifact_digest", "artifact_path": "relative/or/absolute/path"}
      ]
    }
  ]
}

The command never changes mission-readiness state. It exits nonzero unless the
current campaign gate is structurally satisfied and ready for separate technical
review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_external_ingest import (
    batch_decision_as_dict,
    envelope_from_mapping,
    evaluate_external_evidence_batch,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed Worldshepherd QRF external evidence intake")
    parser.add_argument("--manifest", required=True, help="JSON manifest containing evidence envelopes")
    parser.add_argument("--output", required=True, help="Decision artifact path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("manifest must contain a JSON object")
    evidence_raw = payload.get("evidence", [])
    if not isinstance(evidence_raw, list) or not evidence_raw:
        raise SystemExit("manifest.evidence must be a non-empty list")
    preconditions = payload.get("completed_preconditions", [])
    if not isinstance(preconditions, list):
        raise SystemExit("manifest.completed_preconditions must be a list")

    envelopes = [envelope_from_mapping(item) for item in evidence_raw]
    decision = evaluate_external_evidence_batch(
        envelopes,
        base_dir=manifest_path.parent,
        completed_preconditions=[str(item) for item in preconditions],
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(batch_decision_as_dict(decision), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"{output}: project={decision.project_id} current_gate={decision.current_gate_id} "
        f"accepted_records={decision.records_accepted_for_campaign_evaluation}/{decision.records_received} "
        f"ready_for_technical_review={decision.ready_for_technical_review}"
    )
    return 0 if decision.ready_for_technical_review else 2


if __name__ == "__main__":
    raise SystemExit(main())

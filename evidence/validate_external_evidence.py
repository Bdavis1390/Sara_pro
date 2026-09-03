#!/usr/bin/env python3
"""Fail-closed validator for Worldshepherd external evidence gates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROTECTED_CLASSES = {
    "measured_internal_test",
    "hardware_in_loop",
    "physical_lab",
    "field_test",
    "independent_review",
    "partner_review",
    "partner_data",
    "partner_test",
    "clinical_review",
    "regulatory",
    "inventory_authority",
    "commercial_outcome",
    "outcome_calibration",
    "security_ops",
    "release_authority",
    "source_freshness",
}

SYNTHETIC_CLASSES = {"architecture", "simulated", "synthetic", "documented"}


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readiness", default="readiness/portfolio.v1.json")
    ap.add_argument("--closures", default="evidence/closures.v1.json")
    ap.add_argument("--output", default="evidence/external-evidence-report.json")
    args = ap.parse_args()

    readiness = load(args.readiness)
    closures = load(args.closures)
    errors: list[str] = []

    open_gate_index: dict[tuple[str, str], bool] = {}
    for ws in readiness.get("workstreams", []):
        wsid = ws.get("id")
        for gate in ws.get("open_external_gates", []):
            open_gate_index[(wsid, gate)] = True

    seen: set[tuple[str, str]] = set()
    accepted: list[dict] = []
    for closure in closures.get("closures", []):
        key = (closure.get("workstream"), closure.get("gate"))
        if key in seen:
            errors.append(f"duplicate closure record: {key}")
            continue
        seen.add(key)
        if key not in open_gate_index:
            errors.append(f"closure does not match a registered open external gate: {key}")
            continue

        gate_class = closure.get("gate_class")
        evidence_class = str(closure.get("evidence_class", "")).lower()
        refs = closure.get("evidence_refs", [])
        approved = bool(closure.get("approved", False))
        if not gate_class:
            errors.append(f"{key}: gate_class is required")
        if not refs:
            errors.append(f"{key}: at least one evidence_ref is required")
        if not approved:
            errors.append(f"{key}: closure must be explicitly approved")
        if gate_class in PROTECTED_CLASSES and evidence_class in SYNTHETIC_CLASSES:
            errors.append(
                f"{key}: protected gate class {gate_class} cannot be closed by {evidence_class} evidence"
            )
        if gate_class in {"clinical_review", "regulatory", "independent_review", "partner_review", "partner_test"} and not closure.get("external_actor"):
            errors.append(f"{key}: external_actor is required for {gate_class}")
        accepted.append(closure)

    closed_keys = {(c.get("workstream"), c.get("gate")) for c in accepted if (c.get("workstream"), c.get("gate")) in open_gate_index}
    open_rows = []
    for (wsid, gate) in sorted(open_gate_index):
        if (wsid, gate) not in closed_keys:
            open_rows.append({"workstream": wsid, "gate": gate, "status": "OPEN"})

    synthetic = closures.get("synthetic_baselines", [])
    for item in synthetic:
        path = Path(item.get("path", ""))
        status = item.get("status")
        if status == "VERIFIED_CI" and not path.exists():
            errors.append(f"synthetic baseline marked VERIFIED_CI but artifact path is absent: {path}")

    report = {
        "schema": "WS-EXTERNAL-EVIDENCE-REPORT-V1",
        "registered_external_gate_count": len(open_gate_index),
        "accepted_closure_count": len(closed_keys),
        "remaining_open_gate_count": len(open_rows),
        "synthetic_baseline_count": len(synthetic),
        "errors": errors,
        "open_gates": open_rows,
        "claims_boundary": "A synthetic or internal readiness artifact never closes a measured, physical, field, clinical, regulatory, independent-review, partner, or commercial-outcome gate.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"registered external gates: {len(open_gate_index)}")
    print(f"accepted closures: {len(closed_keys)}")
    print(f"remaining open gates: {len(open_rows)}")
    print(f"synthetic baselines tracked: {len(synthetic)}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

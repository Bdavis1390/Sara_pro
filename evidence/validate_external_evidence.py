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
EXTERNAL_ACTOR_CLASSES = {
    "clinical_review",
    "regulatory",
    "independent_review",
    "partner_review",
    "partner_test",
}
MATURITY_ORDER = {
    "architecture": 0,
    "simulated": 1,
    "implemented_software": 2,
    "internal_test": 3,
    "partner_test": 4,
    "independently_replicated": 5,
    "qualified_or_certified": 6,
}


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(c in "0123456789abcdef" for c in digest.lower())


def require_artifact_binding(item: dict, label: str, errors: list[str]) -> None:
    if not isinstance(item.get("run_id"), int) or item["run_id"] <= 0:
        errors.append(f"{label}: positive integer run_id is required")
    if not isinstance(item.get("artifact_id"), int) or item["artifact_id"] <= 0:
        errors.append(f"{label}: positive integer artifact_id is required")
    if not item.get("artifact_name"):
        errors.append(f"{label}: artifact_name is required")
    if not valid_sha256(item.get("artifact_digest")):
        errors.append(f"{label}: artifact_digest must be sha256:<64 hex>")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readiness", default="readiness/portfolio.v1.json")
    ap.add_argument("--closures", default="evidence/closures.v1.json")
    ap.add_argument("--output", default="evidence/external-evidence-report.json")
    args = ap.parse_args()

    readiness = load(args.readiness)
    closures = load(args.closures)
    errors: list[str] = []

    workstreams = {ws.get("id"): ws for ws in readiness.get("workstreams", []) if ws.get("id")}
    open_gate_index: dict[tuple[str, str], bool] = {}
    for wsid, ws in workstreams.items():
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
        if not valid_sha256(closure.get("evidence_digest")):
            errors.append(f"{key}: evidence_digest must be sha256:<64 hex>")
        if not approved:
            errors.append(f"{key}: closure must be explicitly approved")
        if not closure.get("scope_boundary"):
            errors.append(f"{key}: scope_boundary is required")
        if gate_class in PROTECTED_CLASSES and evidence_class in SYNTHETIC_CLASSES:
            errors.append(
                f"{key}: protected gate class {gate_class} cannot be closed by {evidence_class} evidence"
            )
        if gate_class in EXTERNAL_ACTOR_CLASSES and not closure.get("external_actor"):
            errors.append(f"{key}: external_actor is required for {gate_class}")
        accepted.append(closure)

    closed_keys = {
        (c.get("workstream"), c.get("gate"))
        for c in accepted
        if (c.get("workstream"), c.get("gate")) in open_gate_index
    }
    open_rows = []
    for (wsid, gate) in sorted(open_gate_index):
        if (wsid, gate) not in closed_keys:
            open_rows.append({"workstream": wsid, "gate": gate, "status": "OPEN"})

    partial_rows: list[dict] = []
    for item in closures.get("partial_evidence", []):
        key = (item.get("workstream"), item.get("gate"))
        if key not in open_gate_index:
            errors.append(f"partial evidence does not match a registered open gate: {key}")
            continue
        if key in closed_keys:
            errors.append(f"partial evidence cannot also target a fully closed gate: {key}")
        if not item.get("evidence_refs"):
            errors.append(f"{key}: partial evidence needs evidence_refs")
        if not valid_sha256(item.get("evidence_digest")):
            errors.append(f"{key}: partial evidence needs a sha256 evidence_digest")
        if not item.get("supported_scope") or not item.get("excluded_scope"):
            errors.append(f"{key}: partial evidence requires supported_scope and excluded_scope")
        if not bool(item.get("approved", False)):
            errors.append(f"{key}: partial evidence must be explicitly approved")
        partial_rows.append(item)

    synthetic = closures.get("synthetic_baselines", [])
    for item in synthetic:
        label = f"synthetic baseline {item.get('workstream')}"
        status = item.get("status")
        if status not in {"PENDING_CI", "VERIFIED_CI"}:
            errors.append(f"{label}: invalid status {status!r}")
        if status == "VERIFIED_CI":
            require_artifact_binding(item, label, errors)
            if not valid_sha256(item.get("output_sha256")):
                errors.append(f"{label}: output_sha256 must bind the retained result file")
        if not item.get("path"):
            errors.append(f"{label}: logical output path is required")

    effective_maturity = {
        wsid: ws.get("evidence_maturity", "architecture") for wsid, ws in workstreams.items()
    }
    maturity_rows: list[dict] = []
    seen_maturity: set[str] = set()
    for item in closures.get("maturity_updates", []):
        wsid = item.get("workstream")
        target = item.get("to")
        if wsid not in workstreams:
            errors.append(f"maturity update references unknown workstream: {wsid!r}")
            continue
        if wsid in seen_maturity:
            errors.append(f"duplicate maturity update for {wsid}")
            continue
        seen_maturity.add(wsid)
        base = effective_maturity[wsid]
        if base not in MATURITY_ORDER or target not in MATURITY_ORDER:
            errors.append(f"{wsid}: unknown maturity transition {base!r} -> {target!r}")
            continue
        if MATURITY_ORDER[target] <= MATURITY_ORDER[base]:
            errors.append(f"{wsid}: maturity update must be a strict evidence-backed increase ({base} -> {target})")
        evidence_class = str(item.get("evidence_class", "")).lower()
        if target == "simulated" and evidence_class not in {"simulated", "synthetic"}:
            errors.append(f"{wsid}: simulated maturity requires simulated/synthetic evidence")
        if target == "internal_test" and evidence_class != "internal_test":
            errors.append(f"{wsid}: internal_test maturity requires internal_test evidence")
        if not item.get("evidence_refs"):
            errors.append(f"{wsid}: maturity update requires evidence_refs")
        if not valid_sha256(item.get("evidence_digest")):
            errors.append(f"{wsid}: maturity update requires sha256 evidence_digest")
        if not item.get("scope_boundary"):
            errors.append(f"{wsid}: maturity update requires scope_boundary")
        if not bool(item.get("approved", False)):
            errors.append(f"{wsid}: maturity update must be explicitly approved")
        effective_maturity[wsid] = target
        maturity_rows.append({"workstream": wsid, "from": base, "to": target})

    report = {
        "schema": "WS-EXTERNAL-EVIDENCE-REPORT-V2",
        "registered_external_gate_count": len(open_gate_index),
        "accepted_closure_count": len(closed_keys),
        "remaining_open_gate_count": len(open_rows),
        "partial_evidence_count": len(partial_rows),
        "synthetic_baseline_count": len(synthetic),
        "verified_synthetic_baseline_count": sum(1 for x in synthetic if x.get("status") == "VERIFIED_CI"),
        "maturity_update_count": len(maturity_rows),
        "maturity_updates": maturity_rows,
        "effective_evidence_maturity": effective_maturity,
        "errors": errors,
        "closed_gates": [
            {"workstream": wsid, "gate": gate, "status": "CLOSED_WITH_BOUND_EVIDENCE"}
            for wsid, gate in sorted(closed_keys)
        ],
        "partial_evidence": partial_rows,
        "open_gates": open_rows,
        "claims_boundary": "A synthetic or internal readiness artifact never closes a measured, physical, field, clinical, regulatory, independent-review, partner, or commercial-outcome gate. Partial evidence never counts as closure.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"registered external gates: {len(open_gate_index)}")
    print(f"accepted closures: {len(closed_keys)}")
    print(f"remaining open gates: {len(open_rows)}")
    print(f"partial evidence records: {len(partial_rows)}")
    print(f"verified synthetic baselines: {report['verified_synthetic_baseline_count']}/{len(synthetic)}")
    print(f"evidence maturity updates: {len(maturity_rows)}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

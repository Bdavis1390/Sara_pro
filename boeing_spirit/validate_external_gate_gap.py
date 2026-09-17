#!/usr/bin/env python3
"""Validate WS-BOEING-01 external-gate dependency matrix against confidence policy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", default="boeing_spirit/external_gate_gap_matrix.v1.json")
    ap.add_argument("--confidence", default="boeing_spirit/confidence.v1.json")
    ap.add_argument("--output", default="boeing_spirit/evidence/external-gate-gap-report.json")
    args = ap.parse_args()

    matrix = load(args.matrix)
    confidence = load(args.confidence)
    errors: list[str] = []

    if matrix.get("schema") != "WS-BOEING-SPIRIT-EXTERNAL-GATE-GAP-MATRIX-V1":
        errors.append("unexpected matrix schema")
    target = float(confidence.get("target_contact_threshold_pct", -1))
    if float(matrix.get("target_contact_threshold_pct", -2)) != target:
        errors.append("target threshold does not match confidence policy")

    required = list(confidence.get("required_for_contact", []))
    matrix_rows = {row.get("gate"): row for row in matrix.get("gates", [])}
    if set(matrix_rows) != set(required):
        errors.append(f"matrix gates {sorted(matrix_rows)} do not equal required contact gates {sorted(required)}")

    configured_states = {name: gate.get("status") for name, gate in confidence.get("gates", {}).items()}
    cap_map = {cap.get("when_gate"): float(cap.get("cap_pct")) for cap in confidence.get("hard_caps", [])}
    for gate in required:
        row = matrix_rows.get(gate)
        if not row:
            continue
        if row.get("current_state") != configured_states.get(gate):
            errors.append(f"{gate}: matrix state {row.get('current_state')} != confidence state {configured_states.get(gate)}")
        if float(row.get("hard_cap_pct_if_not_closed", -1)) != cap_map.get(gate):
            errors.append(f"{gate}: hard cap mismatch")
        if row.get("self_close_allowed") is not False:
            errors.append(f"{gate}: self_close_allowed must be false")
        if len(row.get("minimum_external_evidence_to_close", [])) < 4:
            errors.append(f"{gate}: insufficient external closure evidence definition")
        if not row.get("pre_contact_work_can_do") or not row.get("pre_contact_work_cannot_do"):
            errors.append(f"{gate}: pre-contact capability boundary incomplete")

    open_caps = []
    for gate in required:
        state = configured_states.get(gate, "missing")
        if state not in {"complete", "verified"}:
            open_caps.append(cap_map[gate])
    effective_precontact_cap = min(open_caps) if open_caps else 100.0
    if float(matrix.get("pre_contact_max_contact_score_pct_under_current_policy", -1)) != effective_precontact_cap:
        errors.append("matrix pre-contact max does not equal active hard-cap minimum")
    if float(matrix.get("current_contact_score_pct", -1)) > effective_precontact_cap:
        errors.append("current contact score exceeds active pre-contact hard cap")
    if not matrix.get("decision_rule", "").startswith("Do not increase"):
        errors.append("decision rule must prohibit preparation-substitution score inflation")

    boundary = matrix.get("claims_boundary", "").lower()
    for term in ["not evidence of boeing/spirit engagement", "measured effect", "independent review", "remediation probability"]:
        if term not in boundary:
            errors.append(f"claims boundary missing {term!r}")

    report = {
        "schema": "WS-BOEING-SPIRIT-EXTERNAL-GATE-GAP-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "required_gate_count": len(required),
        "required_gates": required,
        "active_pre_contact_hard_cap_pct": effective_precontact_cap,
        "target_contact_threshold_pct": target,
        "pre_contact_threshold_reachable_under_current_policy": effective_precontact_cap >= target,
        "contact_gate_effect": "NONE",
        "claims_boundary": "PASS validates dependency bookkeeping only. It does not close any Boeing/Spirit external gate or authorize contact."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed validator for the public Boeing cybersecurity crosswalk."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="boeing_spirit/public_cybersecurity_crosswalk.v1.json")
    ap.add_argument("--output", default="boeing_spirit/evidence/public-cybersecurity-crosswalk-report.json")
    args = ap.parse_args()

    d = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors: list[str] = []
    if d.get("schema") != "WS-BOEING-SPIRIT-PUBLIC-CYBERSECURITY-CROSSWALK-V1":
        errors.append("unexpected schema")
    if d.get("default_data_posture") != "PUBLIC_OR_SYNTHETIC_ONLY":
        errors.append("default data posture must be PUBLIC_OR_SYNTHETIC_ONLY")
    if len(d.get("official_sources", [])) < 5:
        errors.append("at least five public Boeing cybersecurity sources required")
    if len(d.get("applicability_decision_table", [])) < 6:
        errors.append("applicability decision table incomplete")
    if len(d.get("pre_contact_internal_evidence_targets", [])) < 12:
        errors.append("internal evidence target set incomplete")
    if len(d.get("contract_specific_fields_required_before_security_gate_closure", [])) < 12:
        errors.append("contract-specific closure fields incomplete")
    if len(d.get("prohibited_inferences", [])) < 6:
        errors.append("prohibited-inference list incomplete")

    condition_map = {row.get("condition"): row for row in d.get("applicability_decision_table", [])}
    for condition in ["FCI_APPLIES", "CUI_OR_CDI_APPLIES", "EXPORT_CONTROLLED_APPLIES", "CLASSIFIED_APPLIES"]:
        row = condition_map.get(condition)
        if not row:
            errors.append(f"missing condition {condition}")
            continue
        action = row.get("worldshepherd_action", "").lower()
        if condition == "CLASSIFIED_APPLIES":
            if "out_of_scope" not in action:
                errors.append("classified state must be out of scope")
        elif "block" not in action:
            errors.append(f"{condition} must block processing pending authorization")

    effect = d.get("contact_gate_effect", "")
    if not effect.startswith("NONE") or "remains PARTIAL" not in effect:
        errors.append("public cyber crosswalk must have no contact-gate effect and preserve partial security state")

    boundary = d.get("claims_boundary", "")
    for phrase in [
        "not legal advice",
        "CMMC certification",
        "NIST SP 800-171 compliance",
        "Boeing C-SCRM approval",
        "authorization to handle FCI/CUI/CDI/export-controlled data",
    ]:
        if phrase not in boundary:
            errors.append(f"claims boundary missing {phrase!r}")

    report = {
        "schema": "WS-BOEING-SPIRIT-PUBLIC-CYBERSECURITY-CROSSWALK-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "official_source_count": len(d.get("official_sources", [])),
        "applicability_condition_count": len(d.get("applicability_decision_table", [])),
        "contact_gate_effect": "NONE",
        "security_compliance_fit": "partial",
        "claims_boundary": "PASS means the public-source applicability/preparation artifact is structurally fail-closed. It does not establish contractual applicability, CMMC/NIST compliance, SPRS status, Boeing approval, authorization to process controlled information, or security gate closure."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

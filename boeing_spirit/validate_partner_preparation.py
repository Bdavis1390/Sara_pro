#!/usr/bin/env python3
"""Validate Boeing/Spirit partner-pilot and security preparation artifacts.

Passing this validator means the internal templates are structurally complete and
claims-controlled. It never closes external partner/security/contact gates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def nonempty_list(obj: dict, key: str, minimum: int = 1) -> None:
    value = obj.get(key)
    if not isinstance(value, list) or len(value) < minimum:
        raise ValueError(f"{key}: expected list with >= {minimum} items")


def validate_protocol(p: dict) -> list[str]:
    errors: list[str] = []
    try:
        if p.get("schema") != "WS-BOEING-SPIRIT-PARTNER-PILOT-PROTOCOL-V1":
            raise ValueError("unexpected partner protocol schema")
        if "NO PARTNER PILOT AUTHORIZED OR PERFORMED" not in p.get("status", ""):
            raise ValueError("partner protocol status must reject performed/authorized interpretation")
        nonempty_list(p, "entry_prerequisites", 8)
        nonempty_list(p, "phases", 5)
        nonempty_list(p, "candidate_metrics", 8)
        nonempty_list(p, "analysis_requirements", 6)
        nonempty_list(p, "stop_conditions", 6)
        phase_ids = [x.get("id") for x in p["phases"]]
        if phase_ids != ["P0", "P1", "P2", "P3", "P4"]:
            raise ValueError(f"unexpected phase sequence: {phase_ids}")
        for phase in p["phases"]:
            if not phase.get("actions") or not phase.get("exit"):
                raise ValueError(f"{phase.get('id')}: actions/exit required")
        if not str(p.get("contact_gate_effect", "")).startswith("NONE"):
            raise ValueError("partner protocol must have zero external contact-gate effect")
        boundary = p.get("claims_boundary", "").lower()
        for term in ["not evidence of boeing/spirit engagement", "authorization", "probability"]:
            if term not in boundary:
                raise ValueError(f"protocol claims boundary missing {term!r}")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def validate_security(s: dict) -> list[str]:
    errors: list[str] = []
    try:
        if s.get("schema") != "WS-BOEING-SPIRIT-SECURITY-DATA-BOUNDARY-V1":
            raise ValueError("unexpected security boundary schema")
        if s.get("default_posture") != "PUBLIC_OR_SYNTHETIC_ONLY":
            raise ValueError("default posture must remain public/synthetic only")
        nonempty_list(s, "data_classes", 7)
        nonempty_list(s, "required_partner_decisions", 10)
        nonempty_list(s, "internal_controls_to_demonstrate_before_partner_data", 10)
        nonempty_list(s, "prohibited_current_claims", 8)
        class_map = {x.get("class"): x.get("handling", "") for x in s["data_classes"]}
        for class_name in ["PARTNER_PROPRIETARY", "CUI_OR_CDI", "EXPORT_CONTROLLED", "CLASSIFIED"]:
            handling = class_map.get(class_name, "").lower()
            if not handling or ("blocked" not in handling and "out of scope" not in handling):
                raise ValueError(f"{class_name}: must be blocked or out of scope")
        effect = s.get("contact_gate_effect", "")
        if "remains PARTIAL" not in effect:
            raise ValueError("security preparation must not close security_compliance_fit")
        boundary = s.get("claims_boundary", "").lower()
        for term in ["does not establish", "compliance", "partner approval"]:
            if term not in boundary:
                raise ValueError(f"security claims boundary missing {term!r}")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol", default="boeing_spirit/partner_pilot_protocol.v1.json")
    ap.add_argument("--security", default="boeing_spirit/security_data_boundary.v1.json")
    ap.add_argument("--output", default="boeing_spirit/evidence/partner-preparation-report.json")
    args = ap.parse_args()

    protocol = load(args.protocol)
    security = load(args.security)
    errors = validate_protocol(protocol) + validate_security(security)
    report = {
        "schema": "WS-BOEING-SPIRIT-PARTNER-PREPARATION-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "external_gate_updates": {
            "partner_data_access": "missing",
            "partner_pilot": "missing",
            "measured_effect_size": "missing",
            "security_compliance_fit": "partial",
            "independent_review": "missing"
        },
        "contact_gate_effect": "NONE",
        "claims_boundary": "A PASS validates internal preparation artifacts only. It does not authorize Boeing/Spirit contact or close any partner, security, effect-size, independent-review, certification, compliance, or production gate."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

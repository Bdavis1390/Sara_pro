#!/usr/bin/env python3
"""Fail-closed validator for marketplace scan expansions and reusable patterns."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round2", default="marketplace/market_scan_round2_20260903.json")
    ap.add_argument("--patterns", default="marketplace/reusable_solution_patterns.v1.json")
    ap.add_argument("--output", default="marketplace/evidence/marketplace-expansion-report.json")
    args = ap.parse_args()

    scan = load(args.round2)
    patterns = load(args.patterns)
    errors: list[str] = []

    if scan.get("schema") != "WS-MARKETPLACE-SCAN-ROUND2-V1":
        errors.append("unexpected round2 schema")
    if scan.get("score_kind") != "market_prioritization_not_probability_of_remediation_or_award":
        errors.append("round2 score_kind must reject probability interpretation")
    if float(scan.get("default_contact_threshold_pct", -1)) != 98.7:
        errors.append("round2 contact threshold must remain 98.7")
    if float(scan.get("default_precontact_cap_pct", -1)) != 55.0:
        errors.append("round2 precontact cap must remain 55.0")
    if "do not create a sixth" not in scan.get("task_routing", "").lower():
        errors.append("round2 must remain routed through five existing tasks")

    targets = scan.get("new_targets", [])
    if not isinstance(targets, list) or len(targets) < 3:
        errors.append("round2 must contain at least three new targets")
        targets = targets if isinstance(targets, list) else []

    seen: set[str] = set()
    for t in targets:
        tid = str(t.get("id", ""))
        if not tid or tid in seen:
            errors.append(f"invalid or duplicate target id {tid!r}")
        seen.add(tid)
        score = t.get("market_priority_score")
        if not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
            errors.append(f"{tid}: invalid prioritization score")
        if t.get("contact_state") != "DO_NOT_CONTACT_NEW_LANE":
            errors.append(f"{tid}: new target must remain DO_NOT_CONTACT_NEW_LANE")
        if float(t.get("precontact_cap_pct", -1)) != 55.0:
            errors.append(f"{tid}: precontact cap must remain 55")
        if len(t.get("solution_wedge", [])) < 4:
            errors.append(f"{tid}: insufficient solution-wedge detail")
        if not t.get("public_sources"):
            errors.append(f"{tid}: public source required")

    if patterns.get("schema") != "WS-MARKETPLACE-REUSABLE-SOLUTION-PATTERNS-V1":
        errors.append("unexpected patterns schema")
    pats = patterns.get("patterns", [])
    if not isinstance(pats, list) or len(pats) < 5:
        errors.append("expected at least five reusable solution patterns")
        pats = pats if isinstance(pats, list) else []
    for p in pats:
        pid = p.get("id", "unknown")
        for required in ["components", "controls", "precontact_tests", "external_success_metrics"]:
            if not isinstance(p.get(required), list) or len(p.get(required, [])) < 4:
                errors.append(f"{pid}: {required} requires >=4 entries")

    deployment = patterns.get("deployment_rule", "").lower()
    for term in ["does not inherit boeing/spirit readiness", "partner-authorized evidence", "independent review"]:
        if term not in deployment:
            errors.append(f"deployment rule missing {term!r}")

    report = {
        "schema": "WS-MARKETPLACE-EXPANSION-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "round2_target_count": len(targets),
        "reusable_solution_pattern_count": len(pats),
        "new_contact_authorizations": 0,
        "default_contact_threshold_pct": scan.get("default_contact_threshold_pct"),
        "default_precontact_cap_pct": scan.get("default_precontact_cap_pct"),
        "errors": errors,
        "claims_boundary": "PASS validates marketplace expansion structure and fail-closed routing only. It does not establish customer-specific remediation probability, fit in production, interest, contracting, adoption, compliance or permission to contact."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Fail-closed validator for marketplace scan round 4."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_STATES = {"DO_NOT_CONTACT_NEW_LANE", "WATCH_ONLY"}


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("round4 registry must be an object")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="marketplace/market_scan_round4_20260903.json")
    ap.add_argument("--output", default="marketplace/evidence/marketplace-round4-report.json")
    args = ap.parse_args()
    d = load(args.registry)
    errors: list[str] = []

    if d.get("schema") != "WS-MARKETPLACE-SCAN-ROUND4-V1":
        errors.append("unexpected schema")
    if d.get("score_kind") != "market_prioritization_not_probability_of_remediation_or_award":
        errors.append("score_kind must reject probability interpretation")
    if float(d.get("default_contact_threshold_pct", -1)) != 98.7:
        errors.append("contact threshold must remain 98.7")
    if float(d.get("default_precontact_cap_pct", -1)) != 55.0:
        errors.append("precontact cap must remain 55.0")
    if "do not create a sixth" not in d.get("task_routing", "").lower():
        errors.append("must remain folded into five existing tasks")

    targets = d.get("new_targets", [])
    if not isinstance(targets, list) or len(targets) != 5:
        errors.append("round4 must contain exactly five targets")
        targets = targets if isinstance(targets, list) else []

    seen: set[str] = set()
    active = watch = 0
    priority_90 = []
    for t in targets:
        tid = str(t.get("id", ""))
        if not tid or tid in seen:
            errors.append(f"invalid or duplicate id {tid!r}")
        seen.add(tid)
        score = t.get("market_priority_score")
        if not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
            errors.append(f"{tid}: invalid priority score")
        elif float(score) >= 90:
            priority_90.append(tid)
        state = t.get("contact_state")
        if state not in ALLOWED_STATES:
            errors.append(f"{tid}: invalid contact state {state!r}")
        elif state == "WATCH_ONLY":
            watch += 1
        else:
            active += 1
        if float(t.get("precontact_cap_pct", -1)) != 55.0:
            errors.append(f"{tid}: precontact cap must remain 55")
        if len(t.get("solution_wedge", [])) < 5:
            errors.append(f"{tid}: solution wedge requires >=5 bounded elements")
        sources = t.get("public_sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{tid}: at least one public source required")
        if not str(t.get("notes", "")).strip():
            errors.append(f"{tid}: notes/claim boundary required")

    boundary = d.get("claims_boundary", "").lower()
    for term in ["scores rank attention only", "do not establish production", "do not imply distress", "no new target is contact-authorized"]:
        if term not in boundary:
            errors.append(f"claims boundary missing {term!r}")

    report = {
        "schema": "WS-MARKETPLACE-ROUND4-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "target_count": len(targets),
        "active_solution_development_target_count": active,
        "watch_only_target_count": watch,
        "high_priority_90_plus_ids": priority_90,
        "new_contact_authorizations": 0,
        "default_contact_threshold_pct": d.get("default_contact_threshold_pct"),
        "default_precontact_cap_pct": d.get("default_precontact_cap_pct"),
        "errors": errors,
        "claims_boundary": "PASS validates scan structure and claims/contact controls only. It does not establish customer-specific root cause, production effectiveness, remediation probability, interest, contracting, adoption, compliance or permission to contact."
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

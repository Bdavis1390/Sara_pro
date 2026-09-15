#!/usr/bin/env python3
"""Validate the Worldshepherd marketplace integration/quality target registry.

This is a claims-control and routing validator. It does not validate the truth of
external webpages at CI runtime and it does not convert prioritization scores into
probabilities of remediation, contracting, or award.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ALLOWED_SIGNAL_CLASSES = {
    "CONFIRMED_ACQUISITION_CONTROL_STRESS",
    "CONFIRMED_PENDING_MERGER_PLUS_CONTROL_STRESS",
    "CONFIRMED_SPIRIT_INTEGRATION_PLUS_QUALITY_SIGNAL",
    "PENDING_ACQUISITION_WITH_SELLER_INTEGRATION_STRESS",
    "COMPLETED_VERTICAL_INTEGRATION_WITH_PREEXISTING_FAB_CONTROL_STRESS",
    "CONFIRMED_SUPPLIER_SYSTEM_TRANSFORMATION",
    "PENDING_VERTICAL_INTEGRATION_WATCH",
    "CONFIRMED_CONTROL_STRESS",
    "CONFIRMED_CONSOLIDATION_AND_CAPACITY_SCALE",
    "CONFIRMED_PRODUCT_SUPPORT_AND_SUPPLIER_QUALITY_STRESS",
    "COMPLETED_ACQUISITION_PREINTEGRATION_WATCH",
    "CONFIRMED_ITGC_AND_SUPPLIER_RISK",
    "LARGE_PRE_CLOSE_INTEGRATION_WATCH",
    "PRE_CLOSE_INTEGRATION_WATCH",
}

ALLOWED_CONTACT_STATES = {
    "DO_NOT_CONTACT_NEW_LANE",
    "INBOUND_ONLY_EXISTING_CONTROL_HOLD",
    "WATCH_ONLY",
}

EXPECTED_TASKS = {
    "USPTO DOE WEF BDS + Boeing/Spirit Scan",
    "Weekly Brief, Replies + Boeing/Spirit",
    "Defense & Dual-Use + Boeing/Spirit Watch",
    "Pentagon UAP + Boeing/Spirit Aerospace Lessons",
    "Revenue, Partner Replies + Boeing/Spirit Oversight",
}


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("registry must be a JSON object")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="marketplace/integration_quality_targets.v1.json")
    ap.add_argument("--output", default="marketplace/evidence/integration-quality-target-report.json")
    args = ap.parse_args()

    d = load(args.registry)
    errors: list[str] = []

    if d.get("schema") != "WS-MARKETPLACE-INTEGRATION-QUALITY-TARGETS-V1":
        errors.append("unexpected schema")
    if d.get("score_kind") != "market_prioritization_not_probability_of_remediation_or_award":
        errors.append("score kind must explicitly reject probability interpretation")
    if float(d.get("default_contact_threshold_pct", -1)) != 98.7:
        errors.append("default contact threshold must remain 98.7")
    if float(d.get("default_precontact_external_evidence_cap_pct", -1)) != 55.0:
        errors.append("default precontact external-evidence cap must remain 55.0")

    routes = set(d.get("task_routes", []))
    if routes != EXPECTED_TASKS:
        errors.append(f"task routing must use exactly the five existing active lanes: {sorted(routes)}")
    if "do not create a sixth" not in d.get("routing_policy", "").lower():
        errors.append("routing policy must reject creation of a sixth automation")

    targets = d.get("targets", [])
    if not isinstance(targets, list) or len(targets) < 15:
        errors.append("expected at least 15 marketplace targets")
        targets = targets if isinstance(targets, list) else []

    ids = [str(t.get("id", "")) for t in targets]
    duplicate_ids = sorted(k for k, v in Counter(ids).items() if v > 1)
    if duplicate_ids:
        errors.append(f"duplicate target ids: {duplicate_ids}")

    active_targets = 0
    watch_targets = 0
    high_priority = []
    control_stress = []
    for i, t in enumerate(targets):
        prefix = t.get("id") or f"target[{i}]"
        score = t.get("market_priority_score")
        if not isinstance(score, (int, float)) or not (0 <= float(score) <= 100):
            errors.append(f"{prefix}: invalid market_priority_score")
        elif float(score) >= 90:
            high_priority.append(prefix)

        signal = t.get("signal_class")
        if signal not in ALLOWED_SIGNAL_CLASSES:
            errors.append(f"{prefix}: unexpected signal_class {signal!r}")
        if signal and ("CONTROL_STRESS" in signal or "ITGC" in signal):
            control_stress.append(prefix)

        state = t.get("contact_state")
        if state not in ALLOWED_CONTACT_STATES:
            errors.append(f"{prefix}: invalid contact_state {state!r}")
        if state == "WATCH_ONLY":
            watch_targets += 1
        else:
            active_targets += 1

        if float(t.get("precontact_cap_pct", -1)) != 55.0:
            errors.append(f"{prefix}: precontact cap must remain 55.0")
        if not str(t.get("organization", "")).strip():
            errors.append(f"{prefix}: organization required")
        if not str(t.get("observed_signal", "")).strip():
            errors.append(f"{prefix}: observed_signal required")
        if not isinstance(t.get("solution_wedge"), list) or len(t.get("solution_wedge", [])) < 3:
            errors.append(f"{prefix}: at least three bounded solution-wedge elements required")
        sources = t.get("public_sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{prefix}: at least one public source required")
        else:
            for source in sources:
                if not isinstance(source, str) or not source.startswith("https://"):
                    errors.append(f"{prefix}: invalid source {source!r}")

        # A newly discovered registry row is not allowed to self-authorize outreach.
        if state == "DO_NOT_CONTACT_NEW_LANE" and float(t.get("precontact_cap_pct", 100)) >= 98.7:
            errors.append(f"{prefix}: new-lane precontact state cannot reach contact threshold")

    boundary = d.get("claims_boundary", "").lower()
    for required in [
        "not probabilities",
        "does not establish root cause",
        "permission to contact",
    ]:
        if required not in boundary:
            errors.append(f"claims boundary missing {required!r}")

    report = {
        "schema": "WS-MARKETPLACE-INTEGRATION-QUALITY-TARGET-REPORT-V1",
        "result": "PASS" if not errors else "FAIL",
        "target_count": len(targets),
        "active_solution_development_target_count": active_targets,
        "watch_only_target_count": watch_targets,
        "high_priority_90_plus_ids": high_priority,
        "control_stress_ids": control_stress,
        "all_new_target_contact_permitted": False,
        "default_contact_threshold_pct": d.get("default_contact_threshold_pct"),
        "default_precontact_external_evidence_cap_pct": d.get("default_precontact_external_evidence_cap_pct"),
        "task_route_count": len(routes),
        "errors": errors,
        "claims_boundary": (
            "PASS validates registry structure, routing and claims controls only. It does not validate target-specific root cause, "
            "remediation effectiveness, customer interest, eligibility, contracting probability, or permission to contact any new target."
        ),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

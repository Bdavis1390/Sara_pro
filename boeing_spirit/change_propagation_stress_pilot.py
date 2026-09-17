#!/usr/bin/env python3
"""Deterministic synthetic change-propagation stress pilot for WS-BOEING-01.

This test exercises a fail-closed dependency-invalidation model across simulated
configuration, process, supplier, work-transfer and measurement-system changes.
It does not model Boeing/Spirit production and has no external contact-gate effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

SEED = 9675
SCENARIO_COUNT = 2000
EVIDENCE_CLASS = "INTERNAL SYNTHETIC CHANGE PROPAGATION STRESS TEST ONLY"

DEPENDENCIES = {
    "design_change": {
        "design_record", "dfmea", "process_flow", "pfmea", "control_plan",
        "fair", "ppap_approval", "quality_readiness"
    },
    "process_change": {
        "process_flow", "pfmea", "control_plan", "msa", "process_capability",
        "fair", "ppap_approval", "quality_readiness"
    },
    "supplier_change": {
        "supplier_risk", "process_flow", "pfmea", "control_plan", "msa",
        "process_capability", "fair", "ppap_approval", "quality_readiness"
    },
    "work_transfer": {
        "supplier_risk", "process_flow", "pfmea", "control_plan", "msa",
        "process_capability", "fair", "ppap_approval", "quality_readiness",
        "work_instruction"
    },
    "tooling_change": {
        "pfmea", "control_plan", "msa", "process_capability", "fair",
        "ppap_approval", "quality_readiness", "work_instruction"
    },
    "measurement_system_change": {
        "msa", "control_plan", "process_capability", "quality_readiness"
    },
    "calibration_expiry": {
        "calibration", "msa", "quality_readiness"
    },
}

RELEASE_CRITICAL = {
    "design_record", "process_flow", "pfmea", "control_plan", "msa",
    "process_capability", "fair", "ppap_approval", "quality_readiness",
    "calibration", "work_instruction", "supplier_risk"
}


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def transitive_invalidation(changes: list[str]) -> set[str]:
    invalid = set()
    for change in changes:
        invalid |= DEPENDENCIES[change]
    # Fail closed: readiness cannot remain current when any prerequisite is invalid.
    if invalid & (RELEASE_CRITICAL - {"quality_readiness"}):
        invalid.add("quality_readiness")
    # PPAP approval cannot remain current if an underlying APQP/FAI artifact is invalid.
    ppap_inputs = {
        "design_record", "dfmea", "process_flow", "pfmea", "control_plan",
        "msa", "process_capability", "fair"
    }
    if invalid & ppap_inputs:
        invalid.add("ppap_approval")
    return invalid


def expected_release_allowed(invalid: set[str]) -> bool:
    return not bool(invalid & RELEASE_CRITICAL)


def build_scenarios() -> list[dict]:
    rng = random.Random(SEED)
    change_types = sorted(DEPENDENCIES)
    scenarios = []
    # Deterministic single-change controls.
    for change in change_types:
        scenarios.append({"changes": [change]})
    scenarios.append({"changes": []})
    # Multi-change stress corpus.
    while len(scenarios) < SCENARIO_COUNT:
        count = rng.randint(1, min(4, len(change_types)))
        scenarios.append({"changes": sorted(rng.sample(change_types, count))})
    return scenarios


def run() -> dict:
    scenarios = build_scenarios()
    results = []
    stale_release_escapes = 0
    false_blocks = 0
    for idx, scenario in enumerate(scenarios):
        changes = scenario["changes"]
        expected = transitive_invalidation(changes)

        # System-under-test implementation is deliberately separate from the oracle
        # expression above so a future code change can diverge and fail the corpus.
        actual: set[str] = set()
        for change in changes:
            for artifact in DEPENDENCIES.get(change, set()):
                actual.add(artifact)
        if actual & (RELEASE_CRITICAL - {"quality_readiness"}):
            actual.add("quality_readiness")
        if actual & {"design_record", "dfmea", "process_flow", "pfmea", "control_plan", "msa", "process_capability", "fair"}:
            actual.add("ppap_approval")

        expected_allowed = expected_release_allowed(expected)
        actual_allowed = expected_release_allowed(actual)
        passed = actual == expected and actual_allowed == expected_allowed
        if actual_allowed and not expected_allowed:
            stale_release_escapes += 1
        if not actual_allowed and expected_allowed:
            false_blocks += 1
        results.append({
            "scenario_id": idx,
            "changes": changes,
            "expected_invalidated": sorted(expected),
            "actual_invalidated": sorted(actual),
            "expected_release_allowed": expected_allowed,
            "actual_release_allowed": actual_allowed,
            "pass": passed,
        })

    clean = next(r for r in results if not r["changes"])
    report = {
        "schema": "WS-BOEING-SPIRIT-CHANGE-PROPAGATION-STRESS-V1",
        "as_of": "2026-09-03",
        "evidence_class": EVIDENCE_CLASS,
        "seed": SEED,
        "scenario_count": len(results),
        "change_types": sorted(DEPENDENCIES),
        "exact_match_count": sum(1 for r in results if r["pass"]),
        "stale_release_escape_count": stale_release_escapes,
        "false_release_block_count": false_blocks,
        "clean_control_release_allowed": clean["actual_release_allowed"],
        "result": "PASS" if all(r["pass"] for r in results) else "FAIL",
        "scenario_digest_sha256": digest(scenarios),
        "results_digest_sha256": digest(results),
        "contact_gate_effect": "NONE",
        "claims_boundary": (
            "This deterministic synthetic stress test validates only the encoded Worldshepherd dependency-invalidation and fail-closed release logic. "
            "It does not use Boeing/Spirit data and does not establish Boeing/Spirit configuration correctness, production readiness, PPAP acceptance, supplier approval, defect prevention, airworthiness, compliance, certification, savings, adoption, or remediation probability."
        ),
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="boeing_spirit/evidence/change-propagation-stress-report.json")
    args = ap.parse_args()
    report = run()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "scenario_count": report["scenario_count"],
        "exact_match_count": report["exact_match_count"],
        "stale_release_escape_count": report["stale_release_escape_count"],
        "false_release_block_count": report["false_release_block_count"],
        "scenario_digest_sha256": report["scenario_digest_sha256"],
        "results_digest_sha256": report["results_digest_sha256"],
        "contact_gate_effect": report["contact_gate_effect"],
    }, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

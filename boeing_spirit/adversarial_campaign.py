#!/usr/bin/env python3
"""Generate and execute a deterministic combinatorial BS-QIA red-team campaign.

The campaign mutates a clean synthetic supplier-quality record across eight public-signal-
derived failure classes. It is internal synthetic robustness evidence only.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Callable

from boeing_spirit.quality_assurance import BLOCK, PASS, evaluate_record


SCHEMA = "WS-BSQIA-ADVERSARIAL-CAMPAIGN-V1"


def _set_digest(record: dict[str, Any], token: str) -> None:
    record["provenance"]["sha256"] = hashlib.sha256(token.encode("utf-8")).hexdigest()


def mutate_requirement_flowdown(record: dict[str, Any]) -> None:
    record["required_requirements"] = ["ENG-A", "CUST-1", "PO-Q1", "ADVERSARIAL-REQ"]
    record["planned_requirements"] = ["ENG-A", "CUST-1", "PO-Q1"]


def mutate_configuration_revision(record: dict[str, Any]) -> None:
    record["bom_revision"] = "STALE-REVISION"


def mutate_apqp_ppap(record: dict[str, Any]) -> None:
    record["apqp_required"] = True
    record["apqp"]["pfmea"] = False


def mutate_product_process_verification(record: dict[str, Any]) -> None:
    record["ppv_findings"] = [{"id": "ADV-PPV", "severity": "critical", "status": "OPEN"}]


def mutate_escape_rcca(record: dict[str, Any]) -> None:
    record["escapes"] = [{"id": "ADV-NOE", "closure_status": "OPEN", "effectiveness_verified": False}]


def mutate_shipment_readiness(record: dict[str, Any]) -> None:
    record["open_work_count"] = 1


def mutate_evidence_provenance(record: dict[str, Any]) -> None:
    record["provenance"]["sha256"] = "invalid"


def mutate_quality_gate_bypass(record: dict[str, Any]) -> None:
    record["schedule_override_attempted"] = True


MUTATIONS: dict[str, Callable[[dict[str, Any]], None]] = {
    "requirement_flowdown": mutate_requirement_flowdown,
    "configuration_revision": mutate_configuration_revision,
    "apqp_ppap": mutate_apqp_ppap,
    "product_process_verification": mutate_product_process_verification,
    "escape_rcca": mutate_escape_rcca,
    "shipment_readiness": mutate_shipment_readiness,
    "evidence_provenance": mutate_evidence_provenance,
    "quality_gate_bypass": mutate_quality_gate_bypass,
}


def generate_campaign(clean_record: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    clean = copy.deepcopy(clean_record)
    clean["record_id"] = "ADV-CLEAN"
    _set_digest(clean, "ADV-CLEAN")
    cases.append({"case_id": "ADV-CLEAN", "mutations": [], "expected": PASS, "record": clean})

    names = list(MUTATIONS)
    counter = 1
    for width in range(1, len(names) + 1):
        for combination in itertools.combinations(names, width):
            record = copy.deepcopy(clean_record)
            case_id = f"ADV-{counter:04d}"
            record["record_id"] = case_id
            _set_digest(record, case_id)
            for name in combination:
                MUTATIONS[name](record)
            cases.append({"case_id": case_id, "mutations": list(combination), "expected": BLOCK, "record": record})
            counter += 1
    return cases


def run_campaign(clean_record: dict[str, Any]) -> dict[str, Any]:
    cases = generate_campaign(clean_record)
    failures: list[dict[str, Any]] = []
    blocked = 0
    passed = 0
    mutation_hits = {name: 0 for name in MUTATIONS}

    for case in cases:
        result = evaluate_record(case["record"])
        actual = result["disposition"]
        if actual == BLOCK:
            blocked += 1
        elif actual == PASS:
            passed += 1
        for name in case["mutations"]:
            mutation_hits[name] += 1
        if actual != case["expected"]:
            failures.append({
                "case_id": case["case_id"],
                "mutations": case["mutations"],
                "expected": case["expected"],
                "actual": actual,
                "finding_codes": [f["code"] for f in result["findings"]],
            })

    return {
        "schema": SCHEMA,
        "evidence_class": "INTERNAL_ADVERSARIAL_SYNTHETIC_TEST",
        "mutation_dimensions": list(MUTATIONS),
        "case_count": len(cases),
        "clean_case_count": 1,
        "mutated_case_count": len(cases) - 1,
        "blocked_count": blocked,
        "pass_count": passed,
        "mismatch_count": len(failures),
        "mismatches": failures,
        "critical_false_negative_count": sum(1 for f in failures if f["expected"] == BLOCK and f["actual"] == PASS),
        "mutation_case_occurrences": mutation_hits,
        "result": "PASS" if not failures and len(cases) == 256 and blocked == 255 and passed == 1 else "FAIL",
        "contact_decision": "NO_CONTACT",
        "claims_boundary": (
            "A 256-case deterministic combinatorial synthetic campaign tests software fail-closed behavior only. "
            "It does not estimate Boeing/Spirit field effectiveness or satisfy the 98.7 external-contact gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    records = fixture.get("records") or []
    clean = next((r for r in records if r.get("record_id") == "CLEAN-001"), None)
    if not clean:
        raise SystemExit("fixture must contain CLEAN-001")

    report = run_campaign(clean)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "case_count": report["case_count"],
        "blocked_count": report["blocked_count"],
        "pass_count": report["pass_count"],
        "critical_false_negative_count": report["critical_false_negative_count"],
    }, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

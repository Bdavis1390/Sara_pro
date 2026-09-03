#!/usr/bin/env python3
"""Fail-closed external-contact gate for the BS-QIA lane.

The 98.7 threshold is treated as an evidence claim, not a planning score. Synthetic,
internal, proposal, architecture, or partner-readiness evidence can never satisfy it.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SCHEMA = "WS-BSQIA-CONTACT-GATE-REPORT-V1"
TARGET = 0.987
ALPHA = 0.05
REQUIRED_FAILURE_MODES = {
    "requirement_flowdown",
    "configuration_revision",
    "apqp_ppap",
    "product_process_verification",
    "escape_rcca",
    "shipment_readiness",
    "evidence_provenance",
    "quality_gate_bypass",
}
REQUIRED_REVIEW_FIELDS = (
    "security_review",
    "data_rights_review",
    "export_control_review",
    "legal_review",
)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def zero_failure_exact_lower_bound(successes: int, trials: int, alpha: float = ALPHA) -> float:
    """One-sided exact lower confidence bound when every trial succeeds.

    For X=n successes from n Bernoulli trials, the Clopper-Pearson one-sided lower
    bound is alpha ** (1/n). This function intentionally returns 0 if any failure
    occurred because the current contact policy requires a zero-failure acceptance
    corpus and does not attempt a general beta-quantile implementation.
    """
    if trials <= 0 or successes != trials:
        return 0.0
    return alpha ** (1.0 / trials)


def evaluate(evidence: dict[str, Any]) -> dict[str, Any]:
    gates: dict[str, dict[str, Any]] = {}

    def gate(name: str, passed: bool, detail: str) -> None:
        gates[name] = {"pass": bool(passed), "detail": detail}

    evidence_class = evidence.get("evidence_class")
    gate(
        "external_independent_evidence",
        evidence_class == "EXTERNAL_INDEPENDENT_VALIDATION",
        f"evidence_class={evidence_class!r}; required='EXTERNAL_INDEPENDENT_VALIDATION'",
    )

    gate(
        "scope_predeclared_and_frozen",
        evidence.get("scope_predeclared") is True and evidence.get("scope_frozen_before_test") is True,
        "Outcome scope and acceptance criteria must be frozen before test execution.",
    )

    metric = evidence.get("success_metric") or {}
    gate(
        "metric_predeclared",
        bool(metric.get("name")) and bool(metric.get("binary_success_definition")) and metric.get("predeclared") is True,
        "A named binary success metric with a predeclared success definition is required.",
    )

    trials = int(metric.get("trials", 0) or 0)
    successes = int(metric.get("successes", 0) or 0)
    lower_bound = zero_failure_exact_lower_bound(successes, trials)
    gate(
        "statistical_lower_bound_98_7",
        successes == trials and trials >= 229 and lower_bound >= TARGET,
        f"successes={successes}, trials={trials}, one-sided 95% exact lower bound={lower_bound:.6f}; target={TARGET:.3f}",
    )

    critical_false_negatives = int(evidence.get("critical_false_negatives", -1))
    gate(
        "zero_critical_false_negatives",
        critical_false_negatives == 0,
        f"critical_false_negatives={critical_false_negatives}; required=0",
    )

    fpr = evidence.get("false_positive_rate")
    fpr_ok = isinstance(fpr, (int, float)) and 0 <= float(fpr) <= 0.05
    gate("operational_false_positive_burden", fpr_ok, f"false_positive_rate={fpr!r}; current pilot ceiling=0.05")

    counts = evidence.get("failure_mode_counts") or {}
    missing_modes = sorted(REQUIRED_FAILURE_MODES - set(counts))
    sparse_modes = sorted(name for name in REQUIRED_FAILURE_MODES if int(counts.get(name, 0) or 0) < 20)
    gate(
        "stratified_failure_mode_coverage",
        not missing_modes and not sparse_modes,
        f"missing={missing_modes}; modes_with_fewer_than_20_cases={sparse_modes}",
    )

    contexts = evidence.get("independent_contexts") or []
    gate(
        "multi_context_validation",
        isinstance(contexts, list) and len(set(str(x) for x in contexts)) >= 2,
        f"independent_context_count={len(set(str(x) for x in contexts)) if isinstance(contexts, list) else 0}; required>=2",
    )

    reviewer = evidence.get("independent_review") or {}
    gate(
        "independent_review",
        reviewer.get("completed") is True and bool(reviewer.get("reviewer_id")) and bool(reviewer.get("report_digest")),
        "Independent reviewer identity and retained report digest are required.",
    )

    gate(
        "independent_replication",
        int(evidence.get("independent_replication_count", 0) or 0) >= 1,
        f"independent_replication_count={evidence.get('independent_replication_count', 0)}; required>=1",
    )

    gate(
        "representative_interface_validation",
        evidence.get("customer_representative_interface_validation") is True,
        "Representative SAP/MES/QMS/PLM or equivalent workflow/interface validation is required without claiming production authority.",
    )
    gate("ood_robustness", evidence.get("ood_tests_passed") is True, "Predeclared out-of-distribution/degraded-data tests must pass.")
    gate(
        "quality_bypass_red_team",
        evidence.get("quality_gate_bypass_tests_passed") is True,
        "Schedule/role/override bypass red-team tests must pass fail-closed.",
    )

    gate(
        "evidence_custody",
        _is_sha256(evidence.get("evidence_package_sha256")) and bool(evidence.get("replay_instructions")),
        "A SHA-256-bound evidence package and replay instructions are required.",
    )

    reviews = evidence.get("reviews") or {}
    for field in REQUIRED_REVIEW_FIELDS:
        value = reviews.get(field)
        gate(
            field,
            value in {"PASS", "NOT_APPLICABLE_WITH_RATIONALE"},
            f"{field}={value!r}; required PASS or NOT_APPLICABLE_WITH_RATIONALE",
        )

    gate(
        "human_acceptance",
        evidence.get("human_acceptance") is True and bool(evidence.get("human_acceptance_id")),
        "Explicit accountable human acceptance is required after the evidence package is complete.",
    )

    all_pass = all(item["pass"] for item in gates.values())
    probability_status = (
        "EVIDENCE_SUPPORTS_PREDECLARED_SCOPED_SUCCESS_LOWER_BOUND_AT_OR_ABOVE_98_7"
        if all_pass
        else "NOT_ESTIMABLE_AT_98_7_FROM_CURRENT_EVIDENCE"
    )
    decision = "GO_CONTACT" if all_pass else "NO_CONTACT"

    return {
        "schema": SCHEMA,
        "target_probability": TARGET,
        "confidence": 1.0 - ALPHA,
        "decision": decision,
        "probability_status": probability_status,
        "one_sided_exact_lower_bound": lower_bound,
        "gates": gates,
        "failed_gates": [name for name, value in gates.items() if not value["pass"]],
        "claims_boundary": (
            "GO_CONTACT, if reached, supports only the frozen scoped success metric represented by the retained external evidence. "
            "It is not a claim that Worldshepherd can fix all Boeing/Spirit financial, manufacturing, certification, or organizational problems."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    report = evaluate(evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "failed_gate_count": len(report["failed_gates"]),
        "lower_bound": report["one_sided_exact_lower_bound"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

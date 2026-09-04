#!/usr/bin/env python3
"""Deterministic synthetic Boeing/Spirit program-risk evidence pilot.

This internal synthetic test exercises operational contract/program-assumption
controls only. It is not accounting, valuation, legal, or Boeing/Spirit data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EVIDENCE_CLASS = "INTERNAL SYNTHETIC PROGRAM RISK CONTROL TEST ONLY"
AS_OF = "2026-09-03"


def fixture(case_id: str, expected_flags: list[str], **overrides) -> dict:
    base = {
        "case_id": case_id,
        "contract_revision": "C7",
        "program_baseline_contract_revision": "C7",
        "production_rate_revision": "RATE-4",
        "cost_estimate_rate_revision": "RATE-4",
        "quality_costs_linked": True,
        "forecast_revision_owner": "program-controls",
        "forecast_revision_approved": True,
        "forecast_revision_rationale": "baseline refresh",
        "cost_to_complete_evidence": True,
        "off_market_contract_risk_reviewed": True,
        "work_transfer": False,
        "supplier_risk_reassessed": True,
        "material_process_change": False,
        "quality_readiness_reassessed": True,
        "estimate_variance_explained": True,
        "expected_flags": sorted(expected_flags),
    }
    base.update(overrides)
    return base


def build_fixtures() -> list[dict]:
    return [
        fixture(
            "contract-baseline-mismatch",
            ["CONTRACT_BASELINE_MISMATCH"],
            program_baseline_contract_revision="C6",
        ),
        fixture(
            "rate-estimate-stale",
            ["COST_ESTIMATE_RATE_STALE"],
            cost_estimate_rate_revision="RATE-3",
        ),
        fixture(
            "quality-cost-unlinked",
            ["QUALITY_COST_EVIDENCE_UNLINKED"],
            quality_costs_linked=False,
        ),
        fixture(
            "forecast-owner-missing",
            ["FORECAST_OWNER_MISSING"],
            forecast_revision_owner="",
        ),
        fixture(
            "forecast-unapproved",
            ["FORECAST_APPROVAL_MISSING"],
            forecast_revision_approved=False,
        ),
        fixture(
            "forecast-rationale-missing",
            ["FORECAST_RATIONALE_MISSING"],
            forecast_revision_rationale="",
        ),
        fixture(
            "cost-to-complete-evidence-missing",
            ["COST_TO_COMPLETE_EVIDENCE_MISSING"],
            cost_to_complete_evidence=False,
        ),
        fixture(
            "off-market-risk-review-missing",
            ["OFF_MARKET_CONTRACT_RISK_REVIEW_MISSING"],
            off_market_contract_risk_reviewed=False,
        ),
        fixture(
            "work-transfer-risk-stale",
            ["SUPPLIER_RISK_REASSESSMENT_MISSING"],
            work_transfer=True,
            supplier_risk_reassessed=False,
        ),
        fixture(
            "process-change-readiness-stale",
            ["QUALITY_READINESS_REASSESSMENT_MISSING"],
            material_process_change=True,
            quality_readiness_reassessed=False,
        ),
        fixture(
            "variance-unexplained",
            ["ESTIMATE_VARIANCE_UNEXPLAINED"],
            estimate_variance_explained=False,
        ),
        fixture("clean-control", []),
    ]


def detect_flags(record: dict) -> list[str]:
    flags: list[str] = []
    if record.get("contract_revision") != record.get("program_baseline_contract_revision"):
        flags.append("CONTRACT_BASELINE_MISMATCH")
    if record.get("production_rate_revision") != record.get("cost_estimate_rate_revision"):
        flags.append("COST_ESTIMATE_RATE_STALE")
    if not record.get("quality_costs_linked"):
        flags.append("QUALITY_COST_EVIDENCE_UNLINKED")
    if not str(record.get("forecast_revision_owner", "")).strip():
        flags.append("FORECAST_OWNER_MISSING")
    if not record.get("forecast_revision_approved"):
        flags.append("FORECAST_APPROVAL_MISSING")
    if not str(record.get("forecast_revision_rationale", "")).strip():
        flags.append("FORECAST_RATIONALE_MISSING")
    if not record.get("cost_to_complete_evidence"):
        flags.append("COST_TO_COMPLETE_EVIDENCE_MISSING")
    if not record.get("off_market_contract_risk_reviewed"):
        flags.append("OFF_MARKET_CONTRACT_RISK_REVIEW_MISSING")
    if record.get("work_transfer") and not record.get("supplier_risk_reassessed"):
        flags.append("SUPPLIER_RISK_REASSESSMENT_MISSING")
    if record.get("material_process_change") and not record.get("quality_readiness_reassessed"):
        flags.append("QUALITY_READINESS_REASSESSMENT_MISSING")
    if not record.get("estimate_variance_explained"):
        flags.append("ESTIMATE_VARIANCE_UNEXPLAINED")
    return sorted(flags)


def digest_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def run_pilot() -> dict:
    fixtures = build_fixtures()
    results = []
    for record in fixtures:
        detected = detect_flags(record)
        expected = sorted(record["expected_flags"])
        results.append(
            {
                "case_id": record["case_id"],
                "expected_flags": expected,
                "detected_flags": detected,
                "pass": detected == expected,
                "fixture_sha256": digest_json(record),
            }
        )
    passed = all(row["pass"] for row in results)
    return {
        "schema": "WS-BOEING-SPIRIT-SYNTHETIC-PROGRAM-RISK-PILOT-V1",
        "as_of": AS_OF,
        "evidence_class": EVIDENCE_CLASS,
        "result": "PASS" if passed else "FAIL",
        "fixture_count": len(fixtures),
        "results": results,
        "fixtures_sha256": digest_json(fixtures),
        "claims_boundary": (
            "This deterministic synthetic test validates only encoded operational program-risk controls. "
            "It does not use Boeing/Spirit data, does not identify Boeing-specific root causes, and does not "
            "constitute accounting, valuation, legal, audit, financial-control, contract-pricing, or production-effectiveness evidence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="boeing_spirit/evidence/synthetic-program-risk-report.json")
    args = parser.parse_args()
    report = run_pilot()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "fixture_count": report["fixture_count"], "fixtures_sha256": report["fixtures_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic synthetic Boeing/Spirit quality-control rule pilot.

This is an internal synthetic test only. It does not use Boeing/Spirit data and
cannot establish production effectiveness, defect reduction, savings, or compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

AS_OF = date(2026, 9, 3)
EVIDENCE_CLASS = "INTERNAL SYNTHETIC QUALITY CONTROL TEST ONLY"


def fixture(case_id: str, expected_flags: list[str], **overrides):
    base = {
        "case_id": case_id,
        "process_change": False,
        "pfmea_revision": "R3",
        "control_plan_revision": "R3",
        "required_control_plan_revision": "R3",
        "fai_status": "complete",
        "msa_status": "acceptable",
        "spc_out_of_control": False,
        "ncr_open": False,
        "rcca_status": "not_required",
        "capa_due": "2026-10-01",
        "capa_status": "not_required",
        "work_instruction_revision": "WI-7",
        "required_work_instruction_revision": "WI-7",
        "calibration_due": "2026-12-31",
        "travelled_work": False,
        "customer_quality_approval": True,
        "expected_flags": sorted(expected_flags),
    }
    base.update(overrides)
    return base


def build_fixtures():
    return [
        fixture("missing-pfmea", ["MISSING_PFMEA"], pfmea_revision=""),
        fixture(
            "stale-control-plan",
            ["STALE_CONTROL_PLAN"],
            process_change=True,
            control_plan_revision="R2",
            required_control_plan_revision="R3",
        ),
        fixture("incomplete-fai", ["FAI_INCOMPLETE"], fai_status="incomplete"),
        fixture("msa-fail", ["MSA_NOT_ACCEPTABLE"], msa_status="failed"),
        fixture("spc-signal", ["SPC_SIGNAL"], spc_out_of_control=True),
        fixture(
            "ncr-no-rcca",
            ["NCR_NO_RCCA"],
            ncr_open=True,
            rcca_status="missing",
        ),
        fixture(
            "overdue-capa",
            ["OVERDUE_CAPA"],
            capa_due="2026-08-20",
            capa_status="open",
        ),
        fixture(
            "configuration-mismatch",
            ["CONFIG_REV_MISMATCH"],
            work_instruction_revision="WI-6",
            required_work_instruction_revision="WI-7",
        ),
        fixture(
            "expired-calibration",
            ["CALIBRATION_EXPIRED"],
            calibration_due="2026-08-31",
        ),
        fixture(
            "travelled-work-approval",
            ["TRAVELLED_WORK_APPROVAL_MISSING"],
            travelled_work=True,
            customer_quality_approval=False,
        ),
        fixture("clean-control", []),
    ]


def detect_flags(record: dict) -> list[str]:
    flags: list[str] = []

    if not str(record.get("pfmea_revision", "")).strip():
        flags.append("MISSING_PFMEA")

    if record.get("process_change") and (
        record.get("control_plan_revision")
        != record.get("required_control_plan_revision")
    ):
        flags.append("STALE_CONTROL_PLAN")

    if record.get("fai_status") != "complete":
        flags.append("FAI_INCOMPLETE")

    if record.get("msa_status") != "acceptable":
        flags.append("MSA_NOT_ACCEPTABLE")

    if bool(record.get("spc_out_of_control")):
        flags.append("SPC_SIGNAL")

    if record.get("ncr_open") and record.get("rcca_status") not in {
        "complete",
        "verified",
    }:
        flags.append("NCR_NO_RCCA")

    capa_due = date.fromisoformat(record["capa_due"])
    if record.get("capa_status") == "open" and capa_due < AS_OF:
        flags.append("OVERDUE_CAPA")

    if (
        record.get("work_instruction_revision")
        != record.get("required_work_instruction_revision")
    ):
        flags.append("CONFIG_REV_MISMATCH")

    calibration_due = date.fromisoformat(record["calibration_due"])
    if calibration_due < AS_OF:
        flags.append("CALIBRATION_EXPIRED")

    if record.get("travelled_work") and not record.get("customer_quality_approval"):
        flags.append("TRAVELLED_WORK_APPROVAL_MISSING")

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
    defect_cases = [row for row in results if row["expected_flags"]]
    clean_cases = [row for row in results if not row["expected_flags"]]
    true_positive_cases = sum(row["pass"] for row in defect_cases)
    true_negative_cases = sum(row["pass"] for row in clean_cases)

    report = {
        "schema": "WS-BOEING-SPIRIT-SYNTHETIC-QUALITY-PILOT-V1",
        "as_of": AS_OF.isoformat(),
        "evidence_class": EVIDENCE_CLASS,
        "result": "PASS" if passed else "FAIL",
        "fixture_count": len(fixtures),
        "seeded_defect_case_count": len(defect_cases),
        "clean_control_case_count": len(clean_cases),
        "exactly_detected_defect_cases": true_positive_cases,
        "exactly_clean_control_cases": true_negative_cases,
        "results": results,
        "claims_boundary": (
            "This deterministic fixture test validates only the encoded rule behavior "
            "against synthetic cases. It does not use Boeing/Spirit data and does not "
            "establish production effectiveness, defect prevention, financial savings, "
            "regulatory compliance, certification, airworthiness, or adoption."
        ),
    }
    report["fixtures_sha256"] = digest_json(fixtures)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="boeing_spirit/evidence/synthetic-quality-report.json",
    )
    args = parser.parse_args()

    report = run_pilot()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ["result", "fixture_count", "fixtures_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

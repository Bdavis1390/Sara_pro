#!/usr/bin/env python3
"""Bounded Boeing-Spirit-like supplier quality assurance prototype.

This module operates on synthetic or authorized records only. It does not connect to
Boeing, Spirit, SAP, MES, QMS, PLM, or production systems and does not establish
real-world quality performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "WS-BSQIA-ASSURANCE-REPORT-V1"
REQUIRED_APQP_TOOLS = (
    "process_flow",
    "pfmea",
    "control_plan",
    "spc",
    "msa",
    "fai",
)
VALID_SHA256_LEN = 64
BLOCK = "BLOCK_RELEASE"
PASS = "PASS_RELEASE_ASSURANCE"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    problem_class: str


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != VALID_SHA256_LEN:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _finding(code: str, severity: str, message: str, problem_class: str) -> Finding:
    return Finding(code=code, severity=severity, message=message, problem_class=problem_class)


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one bounded quality record and return a replayable disposition."""
    findings: list[Finding] = []

    record_id = str(record.get("record_id", "MISSING_RECORD_ID"))

    # ECHO-like provenance minimum.
    provenance = record.get("provenance") or {}
    if not provenance.get("source_system"):
        findings.append(_finding("PROV_SOURCE_MISSING", "critical", "Source system is missing.", "BSQIA-P07"))
    if not provenance.get("observed_at_utc"):
        findings.append(_finding("PROV_TIME_MISSING", "critical", "Observation timestamp is missing.", "BSQIA-P07"))
    if not _is_sha256(provenance.get("sha256")):
        findings.append(_finding("PROV_DIGEST_INVALID", "critical", "Evidence SHA-256 is absent or invalid.", "BSQIA-P07"))

    # Requirement flow-down: supplier planning must include every predeclared applicable requirement.
    required = set(record.get("required_requirements") or [])
    planned = set(record.get("planned_requirements") or [])
    missing_requirements = sorted(required - planned)
    if missing_requirements:
        findings.append(
            _finding(
                "REQ_FLOWDOWN_GAP",
                "critical",
                f"Supplier planning is missing requirements: {', '.join(missing_requirements)}",
                "BSQIA-P01",
            )
        )

    # Configuration lineage: simplified synthetic contract. Real integration needs authoritative mapping rules.
    expected_revision = record.get("expected_revision")
    for field in ("planning_revision", "bom_revision", "build_record_revision"):
        actual = record.get(field)
        if expected_revision is None or actual != expected_revision:
            findings.append(
                _finding(
                    "CONFIG_REVISION_MISMATCH",
                    "critical",
                    f"{field}={actual!r} does not match expected_revision={expected_revision!r}.",
                    "BSQIA-P02",
                )
            )

    # APQP/PPAP evidence completeness.
    if record.get("apqp_required", False):
        apqp = record.get("apqp") or {}
        missing_tools = [name for name in REQUIRED_APQP_TOOLS if apqp.get(name) is not True]
        if missing_tools:
            findings.append(
                _finding(
                    "APQP_EVIDENCE_INCOMPLETE",
                    "major",
                    f"Required APQP evidence is incomplete: {', '.join(missing_tools)}",
                    "BSQIA-P03",
                )
            )

    if record.get("fai_required", False) and record.get("fai_status") != "APPROVED":
        findings.append(_finding("FAI_NOT_APPROVED", "critical", "Required FAI is not approved.", "BSQIA-P03"))

    if record.get("supplier_qms_status") != "APPROVED":
        findings.append(
            _finding("SUPPLIER_QMS_NOT_APPROVED", "critical", "Supplier QMS status is not APPROVED.", "BSQIA-P04")
        )

    for process in record.get("special_processes") or []:
        if not process.get("qualification_valid", False):
            findings.append(
                _finding(
                    "SPECIAL_PROCESS_QUALIFICATION_INVALID",
                    "critical",
                    f"Special process {process.get('name', 'UNKNOWN')} lacks valid qualification evidence.",
                    "BSQIA-P04",
                )
            )

    for calibration in record.get("calibrations") or []:
        if not calibration.get("valid", False):
            findings.append(
                _finding(
                    "CALIBRATION_INVALID",
                    "critical",
                    f"Calibration {calibration.get('id', 'UNKNOWN')} is invalid or expired.",
                    "BSQIA-P07",
                )
            )

    # Product/process audit findings must be dispositioned.
    for audit_finding in record.get("ppv_findings") or []:
        if audit_finding.get("status") != "CLOSED":
            findings.append(
                _finding(
                    "PPV_FINDING_OPEN",
                    "critical" if audit_finding.get("severity") == "critical" else "major",
                    f"PPV finding {audit_finding.get('id', 'UNKNOWN')} remains open.",
                    "BSQIA-P04",
                )
            )

    # Escape/RCCA/8D closure.
    for escape in record.get("escapes") or []:
        if escape.get("closure_status") != "CLOSED" or not escape.get("effectiveness_verified", False):
            findings.append(
                _finding(
                    "ESCAPE_RCCA_NOT_CLOSED",
                    "critical",
                    f"Escape/RCCA {escape.get('id', 'UNKNOWN')} lacks closed, effectiveness-verified evidence.",
                    "BSQIA-P05",
                )
            )

    # Shipment readiness.
    if int(record.get("open_work_count", 0)) > 0:
        findings.append(
            _finding(
                "OPEN_WORK_AT_RELEASE",
                "critical",
                f"{record.get('open_work_count')} open work item(s) remain before release.",
                "BSQIA-P06",
            )
        )
    if record.get("shipping_documents_complete") is not True:
        findings.append(
            _finding(
                "SHIPPING_EVIDENCE_INCOMPLETE",
                "critical",
                "Required shipment documentation is incomplete.",
                "BSQIA-P06",
            )
        )

    # PRIME-like anti-bypass control: a schedule/production push cannot silently alter quality disposition.
    override_attempt = bool(record.get("schedule_override_attempted", False))
    if override_attempt:
        findings.append(
            _finding(
                "SCHEDULE_OVERRIDE_REQUIRES_SEPARATE_AUTHORITY",
                "critical",
                "Schedule/production override attempted; quality release remains fail-closed.",
                "BSQIA-P08",
            )
        )

    disposition = BLOCK if findings else PASS
    return {
        "record_id": record_id,
        "record_digest": _canonical_digest(record),
        "disposition": disposition,
        "finding_count": len(findings),
        "findings": [asdict(item) for item in findings],
        "claims_boundary": "Synthetic/internal rule evaluation only; not Boeing/Spirit validation or production release authority.",
    }


def evaluate_corpus(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    results = [evaluate_record(record) for record in records]
    expected_pairs = []
    for record, result in zip(records if isinstance(records, list) else [], results):
        expected = record.get("expected_disposition")
        if expected in {BLOCK, PASS}:
            expected_pairs.append((expected, result["disposition"]))

    confusion = {"tp_block": 0, "tn_pass": 0, "fp_block": 0, "fn_pass": 0}
    for expected, actual in expected_pairs:
        if expected == BLOCK and actual == BLOCK:
            confusion["tp_block"] += 1
        elif expected == PASS and actual == PASS:
            confusion["tn_pass"] += 1
        elif expected == PASS and actual == BLOCK:
            confusion["fp_block"] += 1
        elif expected == BLOCK and actual == PASS:
            confusion["fn_pass"] += 1

    evaluated = len(expected_pairs)
    correct = confusion["tp_block"] + confusion["tn_pass"]
    accuracy = correct / evaluated if evaluated else None
    critical_false_negative_count = confusion["fn_pass"]

    return {
        "schema": SCHEMA,
        "evidence_class": "INTERNAL_TEST_ON_SYNTHETIC_DATA",
        "record_count": len(results),
        "labeled_record_count": evaluated,
        "results": results,
        "confusion": confusion,
        "accuracy": accuracy,
        "critical_false_negative_count": critical_false_negative_count,
        "result": "PASS" if evaluated and critical_false_negative_count == 0 and correct == evaluated else "FAIL",
        "external_solution_probability_pct": None,
        "external_solution_probability_status": "NOT_ESTIMABLE_FROM_SYNTHETIC_EVIDENCE",
        "contact_decision": "NO_CONTACT",
        "claims_boundary": (
            "Perfect synthetic behavior does not establish a 98.7% probability of fixing Boeing/Spirit production problems. "
            "External representative and independent validation is required."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise SystemExit("input must contain a non-empty records list")
    report = evaluate_corpus(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "records": report["record_count"],
        "confusion": report["confusion"],
        "contact_decision": report["contact_decision"],
    }, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

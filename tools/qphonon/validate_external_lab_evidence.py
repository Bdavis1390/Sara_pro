#!/usr/bin/env python3
"""Validate the external-laboratory evidence ledger without promoting it to L3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema") != "WS-QPHONON-EXTERNAL-LAB-EVIDENCE-V0.1":
        errors.append("external laboratory evidence schema mismatch")
    if data.get("classification") != "EXTERNAL_PUBLISHED_LABORATORY_EVIDENCE":
        errors.append("classification must remain external published laboratory evidence")
    if data.get("worldshepherd_controlled_experiment") is not False:
        errors.append("external evidence must not be relabeled as Worldshepherd-controlled")
    if data.get("closes_l3_partner_hardware_gate") is not False:
        errors.append("external published evidence must not close the L3 partner hardware gate")

    records = data.get("records")
    if not isinstance(records, list) or len(records) < 3:
        errors.append("at least three independent external laboratory evidence records are required")
        return errors

    ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record {index} must be an object")
            continue
        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"record {index} missing evidence_id")
        elif evidence_id in ids:
            errors.append(f"duplicate evidence_id: {evidence_id}")
        else:
            ids.add(evidence_id)
        for field in ("organization", "title", "doi", "physical_system"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{evidence_id or index} missing {field}")
        findings = record.get("measured_findings")
        if not isinstance(findings, list) or not findings:
            errors.append(f"{evidence_id or index} must contain measured findings")
        does_not_support = record.get("does_not_support")
        if not isinstance(does_not_support, list) or not does_not_support:
            errors.append(f"{evidence_id or index} must retain explicit negative claim boundaries")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="evidence/qphonon/external_lab_evidence_2026-09-17.json",
    )
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: unable to load evidence ledger: {exc}")
        return 1
    errors = validate(data) if isinstance(data, dict) else ["top-level evidence value must be an object"]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("WS-QPHONON external laboratory evidence ledger: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

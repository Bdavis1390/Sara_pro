#!/usr/bin/env python3
"""Fail-closed Boeing/Spirit remediation-confidence validator.

The resulting percentage is an evidence/fit gate, not a calibrated statistical
probability of enterprise remediation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ACCEPTED_CLOSED = {"complete", "verified"}


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def validate_config(config: dict) -> None:
    if config.get("schema") != "WS-BOEING-SPIRIT-CONFIDENCE-V1":
        raise ValueError("unexpected confidence schema")
    if config.get("score_kind") != "evidence_backed_remediation_confidence_not_statistical_probability":
        raise ValueError("score_kind must preserve non-probability boundary")
    factors = config.get("status_factors", {})
    gates = config.get("gates", {})
    if not gates:
        raise ValueError("no confidence gates")
    total_weight = sum(float(g["weight"]) for g in gates.values())
    if abs(total_weight - 100.0) > 1e-9:
        raise ValueError(f"gate weights must sum to 100, got {total_weight}")
    for name, gate in gates.items():
        if gate.get("status") not in factors:
            raise ValueError(f"unknown status for {name}: {gate.get('status')}")
        if float(gate.get("weight", 0)) < 0:
            raise ValueError(f"negative weight for {name}")
    threshold = float(config.get("target_contact_threshold_pct", 0))
    if not (0 <= threshold <= 100):
        raise ValueError("invalid target_contact_threshold_pct")
    if "not a statistical probability" not in config.get("claims_boundary", ""):
        raise ValueError("claims boundary must explicitly reject statistical-probability interpretation")


def apply_synthetic_evidence(statuses: dict, report: dict | None) -> tuple[dict, dict]:
    effective = dict(statuses)
    synthetic = {
        "supplied": report is not None,
        "accepted": False,
        "reason": "no synthetic report supplied",
    }
    if report is None:
        return effective, synthetic

    valid = (
        report.get("schema") == "WS-BOEING-SPIRIT-SYNTHETIC-QUALITY-PILOT-V1"
        and report.get("evidence_class") == "INTERNAL SYNTHETIC QUALITY CONTROL TEST ONLY"
        and report.get("result") == "PASS"
        and report.get("fixture_count", 0) >= 11
        and all(row.get("pass") is True for row in report.get("results", []))
        and "does not use Boeing/Spirit data" in report.get("claims_boundary", "")
    )
    if valid:
        effective["synthetic_pilot"] = "verified"
        synthetic = {
            "supplied": True,
            "accepted": True,
            "reason": "deterministic synthetic fixture report passed exact-match checks",
            "fixtures_sha256": report.get("fixtures_sha256"),
        }
    else:
        synthetic = {
            "supplied": True,
            "accepted": False,
            "reason": "synthetic report failed schema/evidence/result/boundary checks",
        }
    return effective, synthetic


def score(config: dict, synthetic_report: dict | None) -> dict:
    validate_config(config)
    gates = config["gates"]
    factors = config["status_factors"]
    configured_statuses = {name: gate["status"] for name, gate in gates.items()}
    effective_statuses, synthetic = apply_synthetic_evidence(configured_statuses, synthetic_report)

    breakdown = []
    raw = 0.0
    for name, gate in gates.items():
        status = effective_statuses[name]
        weight = float(gate["weight"])
        contribution = weight * float(factors[status])
        raw += contribution
        breakdown.append(
            {
                "gate": name,
                "weight": weight,
                "configured_status": configured_statuses[name],
                "effective_status": status,
                "contribution": round(contribution, 4),
            }
        )

    active_caps = []
    final = raw
    for cap in config.get("hard_caps", []):
        gate_name = cap["when_gate"]
        status = effective_statuses[gate_name]
        allowed = set(cap.get("unless_status_in", []))
        if status not in allowed:
            cap_pct = float(cap["cap_pct"])
            final = min(final, cap_pct)
            active_caps.append(
                {
                    "gate": gate_name,
                    "status": status,
                    "cap_pct": cap_pct,
                    "reason": cap["reason"],
                }
            )

    threshold = float(config["target_contact_threshold_pct"])
    required = config.get("required_for_contact", [])
    required_states = {
        name: effective_statuses.get(name, "missing") for name in required
    }
    required_closed = all(state in ACCEPTED_CLOSED for state in required_states.values())
    official_route_verified = config.get("official_contact_route", {}).get("status") == "verified"
    final = round(max(0.0, min(100.0, final)), 4)
    raw = round(max(0.0, min(100.0, raw)), 4)
    contact_gate_pass = (
        final >= threshold and required_closed and official_route_verified
    )

    return {
        "schema": "WS-BOEING-SPIRIT-CONFIDENCE-REPORT-V1",
        "as_of": config["as_of"],
        "score_kind": config["score_kind"],
        "target_contact_threshold_pct": threshold,
        "raw_weighted_score_pct": raw,
        "evidence_backed_remediation_confidence_pct": final,
        "active_hard_caps": active_caps,
        "gate_breakdown": breakdown,
        "synthetic_evidence": synthetic,
        "required_contact_gate_states": required_states,
        "official_contact_route_verified": official_route_verified,
        "contact_gate_pass": contact_gate_pass,
        "contact_action": (
            "AUTHORIZED_BY_MACHINE_GATE_FOR_HUMAN/AGENT EXECUTION THROUGH OFFICIAL ROUTE"
            if contact_gate_pass
            else "DO_NOT_CONTACT — EXTERNAL VALIDATION GATES REMAIN OPEN"
        ),
        "claims_boundary": config["claims_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="boeing_spirit/confidence.v1.json")
    parser.add_argument("--synthetic-report")
    parser.add_argument(
        "--output",
        default="boeing_spirit/evidence/solution-confidence-report.json",
    )
    args = parser.parse_args()

    config = load_json(args.config)
    synthetic_report = load_json(args.synthetic_report) if args.synthetic_report else None
    report = score(config, synthetic_report)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "raw_weighted_score_pct": report["raw_weighted_score_pct"],
                "evidence_backed_remediation_confidence_pct": report[
                    "evidence_backed_remediation_confidence_pct"
                ],
                "contact_gate_pass": report["contact_gate_pass"],
                "contact_action": report["contact_action"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Deterministic synthetic APQP/PPAP evidence-completeness pilot.

Rules are derived from the internal public-quality crosswalk and are intentionally
contract-applicability aware. This is not Boeing approval or AS9145 certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

AS_OF = "2026-09-03"
EVIDENCE_CLASS = "INTERNAL SYNTHETIC APQP/PPAP CROSSWALK TEST ONLY"

ARTIFACT_KEYS = {
    1: "design_record",
    2: "dfmea",
    3: "process_flow",
    4: "pfmea",
    5: "control_plan",
    6: "msa",
    7: "initial_process_capability",
    8: "packaging_preservation_labeling",
    9: "fair",
    11: "ppap_approval",
}
VALID_REQUIREMENT_STATES = {"REQUIRED", "AS_REQUIRED", "NOT_APPLICABLE", "UNKNOWN"}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_case(case_id: str, expected_flags: list[str], *, seller_designed: bool = False, overrides: dict | None = None) -> dict:
    req = {str(k): "REQUIRED" for k in [3, 4, 5, 11]}
    req.update({str(k): "AS_REQUIRED" for k in [6, 7, 8, 9]})
    req.update({"1": "REQUIRED" if seller_designed else "NOT_APPLICABLE", "2": "REQUIRED" if seller_designed else "NOT_APPLICABLE"})
    evidence = {v: {"present": req[str(k)] in {"REQUIRED", "AS_REQUIRED"}, "revision": "R1", "approved": True} for k, v in ARTIFACT_KEYS.items()}
    case = {
        "case_id": case_id,
        "seller_designed": seller_designed,
        "requirement_state": req,
        "evidence": evidence,
        "process_change": False,
        "affected_elements": [],
        "expected_flags": sorted(expected_flags),
    }
    if overrides:
        for key, value in overrides.items():
            if key == "requirement_state":
                case[key].update(value)
            elif key == "evidence":
                for ekey, eval_ in value.items():
                    case[key][ekey].update(eval_)
            else:
                case[key] = value
    return case


def fixtures() -> list[dict]:
    return [
        make_case("buyer-designed-clean", []),
        make_case("seller-designed-clean", [], seller_designed=True),
        make_case("missing-process-flow", ["MISSING_REQUIRED_ELEMENT_3"], overrides={"evidence": {"process_flow": {"present": False}}}),
        make_case("missing-pfmea", ["MISSING_REQUIRED_ELEMENT_4"], overrides={"evidence": {"pfmea": {"present": False}}}),
        make_case("missing-control-plan", ["MISSING_REQUIRED_ELEMENT_5"], overrides={"evidence": {"control_plan": {"present": False}}}),
        make_case("missing-ppap-approval", ["MISSING_REQUIRED_ELEMENT_11"], overrides={"evidence": {"ppap_approval": {"present": False}}}),
        make_case("seller-design-record-missing", ["MISSING_REQUIRED_ELEMENT_1"], seller_designed=True, overrides={"evidence": {"design_record": {"present": False}}}),
        make_case("seller-dfmea-missing", ["MISSING_REQUIRED_ELEMENT_2"], seller_designed=True, overrides={"evidence": {"dfmea": {"present": False}}}),
        make_case("unknown-applicability", ["UNKNOWN_APPLICABILITY_ELEMENT_6"], overrides={"requirement_state": {"6": "UNKNOWN"}, "evidence": {"msa": {"present": False}}}),
        make_case("required-msa-missing", ["MISSING_REQUIRED_ELEMENT_6"], overrides={"requirement_state": {"6": "REQUIRED"}, "evidence": {"msa": {"present": False}}}),
        make_case("unapproved-fair", ["UNAPPROVED_ELEMENT_9"], overrides={"requirement_state": {"9": "REQUIRED"}, "evidence": {"fair": {"approved": False}}}),
        make_case("process-change-stale-pfmea", ["STALE_AFFECTED_ELEMENT_4"], overrides={"process_change": True, "affected_elements": [4], "evidence": {"pfmea": {"revision": "R0"}}}),
        make_case("process-change-stale-control-plan", ["STALE_AFFECTED_ELEMENT_5"], overrides={"process_change": True, "affected_elements": [5], "evidence": {"control_plan": {"revision": "R0"}}}),
    ]


def detect(case: dict) -> list[str]:
    flags: list[str] = []
    req = case["requirement_state"]
    evidence = case["evidence"]
    for element, key in ARTIFACT_KEYS.items():
        state = req.get(str(element), "UNKNOWN")
        if state not in VALID_REQUIREMENT_STATES:
            flags.append(f"INVALID_REQUIREMENT_STATE_ELEMENT_{element}")
            continue
        if state == "UNKNOWN":
            flags.append(f"UNKNOWN_APPLICABILITY_ELEMENT_{element}")
            continue
        if state == "NOT_APPLICABLE":
            continue
        item = evidence.get(key, {})
        if state == "REQUIRED" and not item.get("present"):
            flags.append(f"MISSING_REQUIRED_ELEMENT_{element}")
            continue
        if item.get("present") and not item.get("approved"):
            flags.append(f"UNAPPROVED_ELEMENT_{element}")
        if case.get("process_change") and element in case.get("affected_elements", []) and item.get("revision") != "R1":
            flags.append(f"STALE_AFFECTED_ELEMENT_{element}")
    return sorted(flags)


def run() -> dict:
    rows = []
    all_cases = fixtures()
    for case in all_cases:
        actual = detect(case)
        expected = sorted(case["expected_flags"])
        rows.append({"case_id": case["case_id"], "expected_flags": expected, "detected_flags": actual, "pass": actual == expected, "fixture_sha256": digest(case)})
    return {
        "schema": "WS-BOEING-SPIRIT-SYNTHETIC-PPAP-CROSSWALK-PILOT-V1",
        "as_of": AS_OF,
        "evidence_class": EVIDENCE_CLASS,
        "fixture_count": len(rows),
        "result": "PASS" if all(r["pass"] for r in rows) else "FAIL",
        "results": rows,
        "fixtures_sha256": digest(all_cases),
        "claims_boundary": "This test validates only Worldshepherd's synthetic, contract-applicability-aware APQP/PPAP evidence rules. It is not a Boeing-approved interpretation and does not establish AS9145/AS9100/D6-82479/Q017 compliance, PPAP acceptance, supplier approval, surveillance results, product acceptance, or production effectiveness."
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="boeing_spirit/evidence/synthetic-ppap-crosswalk-report.json")
    args = ap.parse_args()
    report = run()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "fixture_count": report["fixture_count"], "fixtures_sha256": report["fixtures_sha256"]}, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

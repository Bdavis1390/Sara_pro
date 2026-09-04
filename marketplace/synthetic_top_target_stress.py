#!/usr/bin/env python3
"""Deterministic synthetic stress test for high-priority marketplace solution packages.

This validates encoded fail-closed control logic against synthetic fixtures only.
It uses no target data and has no external/contact gate effect.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

AS_OF = "2026-09-03"
EVIDENCE_CLASS = "INTERNAL SYNTHETIC MULTI-TARGET CONTROL STRESS ONLY"


def digest(v: object) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_packages(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flag(control: str) -> str:
    return "MISSING_OR_INVALID_" + control.upper()


def detect(record: dict, controls: list[str]) -> list[str]:
    return sorted(flag(c) for c in controls if record.get(c) is not True)


def fixtures_for_target(target: dict) -> list[dict]:
    controls = list(target["required_controls"])
    base = {c: True for c in controls}
    out = []
    for control in controls:
        record = dict(base)
        record[control] = False
        out.append({
            "target_id": target["id"],
            "case_id": f"{target['id']}-{control}-invalid",
            "record": record,
            "expected_flags": [flag(control)],
        })
    out.append({
        "target_id": target["id"],
        "case_id": f"{target['id']}-multi-fault",
        "record": {**base, controls[0]: False, controls[-1]: False},
        "expected_flags": sorted([flag(controls[0]), flag(controls[-1])]),
    })
    out.append({
        "target_id": target["id"],
        "case_id": f"{target['id']}-clean-control",
        "record": base,
        "expected_flags": [],
    })
    return out


def run(packages: dict) -> dict:
    targets = packages.get("targets", [])
    target_map = {t["id"]: t for t in targets}
    fixtures = []
    for target in targets:
        fixtures.extend(fixtures_for_target(target))
    results = []
    by_target = {}
    for case in fixtures:
        target = target_map[case["target_id"]]
        detected = detect(case["record"], target["required_controls"])
        expected = sorted(case["expected_flags"])
        passed = detected == expected
        results.append({
            "target_id": case["target_id"],
            "case_id": case["case_id"],
            "expected_flags": expected,
            "detected_flags": detected,
            "pass": passed,
            "fixture_sha256": digest(case),
        })
        row = by_target.setdefault(case["target_id"], {"fixture_count": 0, "pass_count": 0})
        row["fixture_count"] += 1
        row["pass_count"] += int(passed)
    all_pass = all(r["pass"] for r in results)
    return {
        "schema": "WS-MARKETPLACE-SYNTHETIC-TOP-TARGET-STRESS-V1",
        "as_of": AS_OF,
        "evidence_class": EVIDENCE_CLASS,
        "result": "PASS" if all_pass else "FAIL",
        "target_count": len(targets),
        "fixture_count": len(fixtures),
        "pass_count": sum(int(r["pass"]) for r in results),
        "by_target": by_target,
        "fixtures_sha256": digest(fixtures),
        "results_sha256": digest(results),
        "results": results,
        "external_gate_updates": {
            "partner_data_access": "none",
            "partner_pilot": "none",
            "measured_effect_size": "none",
            "security_compliance_fit": "none",
            "independent_review": "none"
        },
        "contact_gate_effect": "NONE",
        "claims_boundary": "PASS validates only encoded synthetic control detection for the eight target-specific public-source mappings. It uses no target data and does not establish target root cause, product quality, safety, compliance, production effectiveness, remediation probability, customer interest or permission to contact."
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--packages',default='marketplace/top_target_solution_packages.v1.json')
    ap.add_argument('--output',default='marketplace/evidence/top-target-synthetic-stress-report.json')
    a=ap.parse_args()
    report=run(load_packages(a.packages))
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['result','target_count','fixture_count','pass_count','fixtures_sha256','results_sha256','contact_gate_effect']},indent=2))
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())

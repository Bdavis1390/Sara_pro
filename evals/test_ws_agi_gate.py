#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

from ws_agi_gate import determine_state, evaluate_level, validate_evidence


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "ws_agi_gate_v1.json").read_text(encoding="utf-8"))


def complete_evidence():
    return [
        {
            "system_id": "TEST",
            "system_version": "test-v1",
            "evaluator": "unit-test",
            "benchmark_version": "synthetic",
            "evaluation_date": "2026-09-11",
            "environment": "test",
            "tools_and_permissions": "test",
            "trial_count": 1,
            "score": "synthetic",
            "human_baseline": "synthetic",
            "contamination_controls": "synthetic",
            "integrity_adjudication": "synthetic",
            "source_or_artifact_hash": "synthetic",
            "claim_state": "PROVEN_INTERNALLY",
        }
    ]


def metrics_for(level):
    values = {}
    for name, rules in CONFIG["required_metrics"].items():
        values[name] = rules[level]["value"]
    return values


class AGIGateTests(unittest.TestCase):
    def test_missing_metrics_cannot_pass(self):
        passed, checks = evaluate_level({}, CONFIG["required_metrics"], "candidate")
        self.assertFalse(passed)
        self.assertTrue(all(check["status"] == "UNKNOWN" for check in checks))

    def test_exact_candidate_thresholds_pass_candidate_only(self):
        metrics = metrics_for("candidate")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate_evidence(
            {"evidence": complete_evidence()}, CONFIG["evidence_required_fields"]
        )
        self.assertTrue(candidate_pass)
        self.assertFalse(verified_pass)
        self.assertEqual(
            determine_state(candidate_pass, verified_pass, evidence["valid"]),
            "AGI_CANDIDATE",
        )

    def test_exact_verified_thresholds_pass(self):
        metrics = metrics_for("verified")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate_evidence(
            {"evidence": complete_evidence()}, CONFIG["evidence_required_fields"]
        )
        self.assertTrue(candidate_pass)
        self.assertTrue(verified_pass)
        self.assertEqual(
            determine_state(candidate_pass, verified_pass, evidence["valid"]),
            "AGI_VERIFIED",
        )

    def test_invalid_evidence_blocks_promotion(self):
        metrics = metrics_for("verified")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate_evidence({"evidence": [{}]}, CONFIG["evidence_required_fields"])
        self.assertFalse(evidence["valid"])
        self.assertEqual(
            determine_state(candidate_pass, verified_pass, evidence["valid"]),
            "BELOW_AGI",
        )


if __name__ == "__main__":
    unittest.main()

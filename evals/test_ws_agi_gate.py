#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

from ws_agi_gate import (
    determine_state,
    evaluate_level,
    preserve_deployment_state,
    summarize_lanes,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "config" / "ws_agi_gate_v1.json").read_text(encoding="utf-8"))


def complete_evidence():
    metric_names = list(CONFIG["required_metrics"])
    return [
        {
            "evidence_id": "unit-test:all-metrics",
            "metric_names": metric_names,
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
            "source_or_artifact_hash": "sha256:synthetic",
            "task_hash": "sha256:synthetic-task",
            "grader_version": "test-v1",
            "rerun_count": 0,
            "human_adjudication": "synthetic",
            "claim_state": "PROVEN_INTERNALLY",
        }
    ]


def metrics_for(level):
    return {
        name: rules[level]["value"]
        for name, rules in CONFIG["required_metrics"].items()
    }


def validate(bundle):
    return validate_evidence(
        bundle,
        CONFIG["evidence_required_fields"],
        required_metrics=list(CONFIG["required_metrics"]),
        allowed_claim_states=CONFIG["claim_states"],
    )


class AGIGateTests(unittest.TestCase):
    def test_missing_metrics_cannot_pass(self):
        passed, checks = evaluate_level({}, CONFIG["required_metrics"], "candidate")
        self.assertFalse(passed)
        self.assertTrue(all(check["status"] == "UNKNOWN" for check in checks))

    def test_exact_candidate_thresholds_pass_candidate_only(self):
        metrics = metrics_for("candidate")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate({"evidence": complete_evidence()})
        self.assertTrue(evidence["valid"])
        self.assertTrue(candidate_pass)
        self.assertFalse(verified_pass)
        self.assertEqual(determine_state(candidate_pass, verified_pass, True), "AGI_CANDIDATE")

    def test_exact_verified_thresholds_pass(self):
        metrics = metrics_for("verified")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate({"evidence": complete_evidence()})
        self.assertTrue(evidence["valid"])
        self.assertTrue(candidate_pass)
        self.assertTrue(verified_pass)
        self.assertEqual(determine_state(candidate_pass, verified_pass, True), "AGI_VERIFIED")

    def test_invalid_evidence_blocks_promotion(self):
        metrics = metrics_for("verified")
        candidate_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "candidate")
        verified_pass, _ = evaluate_level(metrics, CONFIG["required_metrics"], "verified")
        evidence = validate({"evidence": [{}]})
        self.assertFalse(evidence["valid"])
        self.assertEqual(
            determine_state(candidate_pass, verified_pass, evidence["valid"]),
            "BELOW_AGI",
        )

    def test_unmapped_metric_blocks_evidence(self):
        records = complete_evidence()
        records[0]["metric_names"] = records[0]["metric_names"][:-1]
        evidence = validate({"evidence": records})
        self.assertFalse(evidence["valid"])
        self.assertTrue(any("without evidence mapping" in error for error in evidence["errors"]))

    def test_duplicate_evidence_id_is_rejected(self):
        records = complete_evidence() * 2
        evidence = validate({"evidence": records})
        self.assertFalse(evidence["valid"])
        self.assertTrue(any("duplicate evidence_id" in error for error in evidence["errors"]))

    def test_invalidated_metric_blocks_threshold_pass(self):
        metrics = metrics_for("verified")
        blocked_metric = "metr_50pct_horizon_hours"
        validity = {blocked_metric: {"valid": False, "reason": "outside reliable range"}}
        passed, checks = evaluate_level(
            metrics, CONFIG["required_metrics"], "verified", validity
        )
        self.assertFalse(passed)
        check = next(item for item in checks if item["metric"] == blocked_metric)
        self.assertEqual(check["status"], "BLOCKED")

    def test_overwatch_lane_uses_worst_metric_status(self):
        checks = [
            {"metric": "a", "status": "PASS", "actual": 1, "target": 1},
            {"metric": "b", "status": "UNKNOWN", "actual": None, "target": 1},
        ]
        lanes = summarize_lanes(checks, {"lane": ["a", "b"]})
        self.assertEqual(lanes["lane"]["status"], "UNKNOWN")

    def test_deployment_state_is_preserved(self):
        for state in CONFIG["deployment_states"]:
            self.assertEqual(
                preserve_deployment_state({"deployment_state": state}, CONFIG["deployment_states"]),
                state,
            )
        with self.assertRaises(ValueError):
            preserve_deployment_state(
                {"deployment_state": "AUTO_PROMOTE"}, CONFIG["deployment_states"]
            )


if __name__ == "__main__":
    unittest.main()

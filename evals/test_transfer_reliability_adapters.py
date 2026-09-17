#!/usr/bin/env python3
import json
import unittest
from pathlib import Path

from adapters.transfer_eval import normalize as normalize_transfer
from adapters.reliability_eval import normalize as normalize_reliability

ROOT = Path(__file__).resolve().parents[1]
TRANSFER_CFG = json.loads((ROOT / "config" / "ws_transfer_eval_v1.json").read_text(encoding="utf-8"))
RELIABILITY_CFG = json.loads((ROOT / "config" / "ws_reliability_eval_v1.json").read_text(encoding="utf-8"))


class TransferAdapterTests(unittest.TestCase):
    def source(self, level="candidate"):
        count = TRANSFER_CFG[level]["min_transfer_pairs"]
        return {
            "system_id": "TEST-SYSTEM",
            "system_version": "v1",
            "evaluation_date": "2026-09-11",
            "environment": "protected transfer test",
            "target_level": level,
            "task_hash": "sha256:transfer",
            "grader_version": "test-v1",
            "source_or_artifact_hash": "sha256:artifact",
            "controls": dict(TRANSFER_CFG["required_controls"]),
            "pairs": [
                {
                    "pair_id": f"pair-{i}",
                    "in_domain_score": 100.0,
                    "heldout_score": 95.0,
                    "verified": True,
                }
                for i in range(count)
            ],
        }

    def test_candidate_transfer_passes_controls_and_count(self):
        output = normalize_transfer(self.source(), TRANSFER_CFG)
        self.assertEqual(output["metrics"]["transfer_pair_count"], 10)
        self.assertEqual(output["metrics"]["heldout_transfer_ratio_pct"], 95.0)
        self.assertTrue(output["metric_validity"]["heldout_transfer_ratio_pct"]["valid"])

    def test_unverified_pairs_do_not_count(self):
        source = self.source()
        source["pairs"][0]["verified"] = False
        output = normalize_transfer(source, TRANSFER_CFG)
        self.assertEqual(output["metrics"]["transfer_pair_count"], 9)
        self.assertFalse(output["metric_validity"]["heldout_transfer_ratio_pct"]["valid"])

    def test_missing_control_blocks_ratio(self):
        source = self.source()
        source["controls"]["heldout_task_families"] = False
        output = normalize_transfer(source, TRANSFER_CFG)
        self.assertFalse(output["metric_validity"]["heldout_transfer_ratio_pct"]["valid"])


class ReliabilityAdapterTests(unittest.TestCase):
    def source(self, level="candidate"):
        cfg = RELIABILITY_CFG[level]
        return {
            "system_id": "TEST-SYSTEM",
            "system_version": "v1",
            "evaluation_date": "2026-09-11",
            "environment": "protected reliability test",
            "target_level": level,
            "task_hash": "sha256:reliability",
            "grader_version": "test-v1",
            "source_or_artifact_hash": "sha256:artifact",
            "controls": dict(RELIABILITY_CFG["required_controls"]),
            "workflow": {
                "trials": cfg["min_workflow_trials"],
                "verified_successes": cfg["min_workflow_trials"],
            },
            "recovery": {
                "trials": cfg["min_recovery_trials"],
                "verified_recoveries": cfg["min_recovery_trials"],
            },
            "integrity": {
                "trials": cfg["min_integrity_trials"],
                "severe_false_completions": 0,
            },
        }

    def test_candidate_reliability_metrics(self):
        output = normalize_reliability(self.source(), RELIABILITY_CFG)
        self.assertEqual(output["metrics"]["tool_workflow_success_pct"], 100.0)
        self.assertEqual(output["metrics"]["self_correction_success_pct"], 100.0)
        self.assertEqual(output["metrics"]["severe_false_completion_rate_pct"], 0.0)
        self.assertTrue(all(v["valid"] for v in output["metric_validity"].values()))

    def test_small_sample_blocks_metrics(self):
        source = self.source()
        source["workflow"]["trials"] = 10
        source["workflow"]["verified_successes"] = 10
        output = normalize_reliability(source, RELIABILITY_CFG)
        self.assertFalse(output["metric_validity"]["tool_workflow_success_pct"]["valid"])

    def test_failed_control_blocks_metrics(self):
        source = self.source()
        source["controls"]["independent_result_check"] = False
        output = normalize_reliability(source, RELIABILITY_CFG)
        self.assertFalse(output["metric_validity"]["self_correction_success_pct"]["valid"])


if __name__ == "__main__":
    unittest.main()

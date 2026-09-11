#!/usr/bin/env python3
import unittest

from adapters.arc_agi_3 import normalize as normalize_arc
from adapters.metr_time_horizon import normalize as normalize_metr


class ARCAdapterTests(unittest.TestCase):
    def base_source(self):
        return {
            "system_id": "GPT-6-ASTRA",
            "system_version": "astra-test",
            "evaluation_date": "2026-09-02",
            "benchmark_version": "ARC-AGI-3 Semi-Private",
            "environment": "verified external evaluation",
            "source_url": "https://arcprize.org/results/openai-gpt-6-astra",
            "task_hash": "sha256:semi-private-task-set",
            "grader_version": "arc-agi-3-verifier",
            "results": [
                {
                    "harness": "standard",
                    "score_pct": 62.71,
                    "verified": True,
                    "reasoning_level": "max",
                },
                {
                    "harness": "provider_adapter",
                    "score_pct": 99.95,
                    "verified": True,
                    "reasoning_level": "high",
                },
            ],
        }

    def test_harnesses_remain_separate(self):
        output = normalize_arc(self.base_source())
        self.assertEqual(output["metrics"]["arc_agi_3_standard_score_pct"], 62.71)
        self.assertEqual(
            output["metrics"]["arc_agi_3_provider_adapter_score_pct"], 99.95
        )
        self.assertEqual(len(output["evidence"]), 2)

    def test_only_verified_results_are_admitted(self):
        source = self.base_source()
        source["results"][0]["verified"] = False
        output = normalize_arc(source)
        self.assertNotIn("arc_agi_3_standard_score_pct", output["metrics"])
        self.assertIn("arc_agi_3_provider_adapter_score_pct", output["metrics"])

    def test_out_of_range_score_rejected(self):
        source = self.base_source()
        source["results"][0]["score_pct"] = 101
        with self.assertRaises(ValueError):
            normalize_arc(source)


class METRAdapterTests(unittest.TestCase):
    def base_source(self):
        return {
            "system_id": "FRONTIER-REFERENCE",
            "system_version": "reference-2026-05",
            "evaluation_date": "2026-05-08",
            "benchmark_version": "TH 1.1",
            "environment": "public frontier reference",
            "source_url": "https://metr.org/time-horizons/",
            "task_hash": "sha256:th-1.1-suite",
            "grader_version": "metr-th-1.1",
            "reliable_max_hours": 16,
            "horizon_80pct_hours": 1.5,
            "horizon_50pct_hours": 12.0,
            "suite_domains": ["software engineering", "machine learning", "cybersecurity"],
        }

    def test_within_range_measurements_remain_valid(self):
        output = normalize_metr(self.base_source())
        self.assertTrue(output["metric_validity"]["metr_80pct_horizon_hours"]["valid"])
        self.assertTrue(output["metric_validity"]["metr_50pct_horizon_hours"]["valid"])

    def test_beyond_reliable_range_is_blocked_not_deleted(self):
        source = self.base_source()
        source["horizon_50pct_hours"] = 20.0
        output = normalize_metr(source)
        self.assertEqual(output["metrics"]["metr_50pct_horizon_hours"], 20.0)
        self.assertFalse(output["metric_validity"]["metr_50pct_horizon_hours"]["valid"])
        self.assertIn("exceeds source reliable range", output["metric_validity"]["metr_50pct_horizon_hours"]["reason"])

    def test_suite_saturation_can_invalidate_all_horizon_metrics(self):
        source = self.base_source()
        source["suite_saturation_warning"] = True
        output = normalize_metr(source)
        self.assertFalse(output["metric_validity"]["metr_80pct_horizon_hours"]["valid"])
        self.assertFalse(output["metric_validity"]["metr_50pct_horizon_hours"]["valid"])


if __name__ == "__main__":
    unittest.main()

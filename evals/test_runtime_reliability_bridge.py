#!/usr/bin/env python3
import unittest

from runtime_reliability_bridge import aggregate


class RuntimeReliabilityBridgeTests(unittest.TestCase):
    def base_source(self):
        return {
            "system_id": "WS-TEST",
            "system_version": "v-test",
            "evaluation_date": "2026-09-11",
            "environment": "protected-test",
            "target_level": "candidate",
            "grader_version": "independent-grader-v1",
            "source_or_artifact_hash": "sha256:artifact",
            "controls": {
                "heldout_tasks": True,
                "independent_result_check": True,
                "task_set_fixed_before_run": True,
                "retain_failed_tasks": True,
            },
            "trials": [
                {
                    "trial_id": "wf-pass",
                    "planner_identity": "provider-a:planner",
                    "final_state_evaluator_identity": "provider-b:grader",
                    "controller_status": "SUCCESS",
                    "independent_final_state_pass": True,
                    "integrity_severity": "none",
                    "steps": [
                        {
                            "verification": {
                                "success": True,
                                "recoverable": False,
                            }
                        }
                    ],
                },
                {
                    "trial_id": "repair-pass",
                    "planner_identity": "provider-a:planner",
                    "final_state_evaluator_identity": "provider-b:grader",
                    "controller_status": "SUCCESS",
                    "independent_final_state_pass": True,
                    "integrity_severity": "none",
                    "steps": [
                        {
                            "verification": {
                                "success": False,
                                "recoverable": True,
                            }
                        },
                        {
                            "verification": {
                                "success": True,
                                "recoverable": False,
                            }
                        },
                    ],
                },
                {
                    "trial_id": "false-complete",
                    "planner_identity": "provider-a:planner",
                    "final_state_evaluator_identity": "provider-b:grader",
                    "controller_status": "SUCCESS",
                    "independent_final_state_pass": False,
                    "integrity_severity": "severe",
                    "steps": [
                        {
                            "verification": {
                                "success": True,
                                "recoverable": False,
                            }
                        }
                    ],
                },
            ],
        }

    def test_counts_are_derived_from_independent_final_state(self):
        result = aggregate(self.base_source())
        self.assertEqual(result["workflow"], {"trials": 3, "verified_successes": 2})
        self.assertEqual(result["recovery"], {"trials": 1, "verified_recoveries": 1})
        self.assertEqual(result["integrity"], {"trials": 3, "severe_false_completions": 1})
        self.assertTrue(result["task_hash"].startswith("sha256:"))

    def test_same_planner_and_final_evaluator_is_rejected(self):
        source = self.base_source()
        source["trials"][0]["final_state_evaluator_identity"] = source["trials"][0]["planner_identity"]
        with self.assertRaises(ValueError):
            aggregate(source)

    def test_duplicate_trial_id_is_rejected(self):
        source = self.base_source()
        source["trials"][1]["trial_id"] = source["trials"][0]["trial_id"]
        with self.assertRaises(ValueError):
            aggregate(source)


if __name__ == "__main__":
    unittest.main()

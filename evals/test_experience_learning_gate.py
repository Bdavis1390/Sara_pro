#!/usr/bin/env python3
import unittest

from experience_ingest import ingest
from runtime.learning_gate import LearningGateConfig, compare_learning_candidate


class ExperienceIngestTests(unittest.TestCase):
    def source(self):
        return {
            "system_id": "WS",
            "system_version": "test-v1",
            "task_profiles": {
                "pass-1": {
                    "task_family": "analysis",
                    "tags": ["files", "verification"],
                    "strategy_summary": "inspect evidence before conclusion",
                },
                "fail-1": {
                    "task_family": "analysis",
                    "tags": ["files"],
                    "strategy_summary": "used incomplete evidence",
                },
            },
            "trials": [
                {
                    "trial_id": "pass-1",
                    "planner_identity": "a:planner",
                    "final_state_evaluator_identity": "b:grader",
                    "controller_status": "SUCCESS",
                    "independent_final_state_pass": True,
                    "integrity_severity": "none",
                    "independent_feedback": "correct",
                    "steps": [{"status": "VERIFIED"}],
                },
                {
                    "trial_id": "fail-1",
                    "planner_identity": "a:planner",
                    "final_state_evaluator_identity": "b:grader",
                    "controller_status": "SUCCESS",
                    "independent_final_state_pass": False,
                    "integrity_severity": "major",
                    "independent_feedback": "final claim did not match evidence",
                    "steps": [{"status": "VERIFIED"}],
                },
            ],
        }

    def test_positive_and_negative_experience_are_both_preserved(self):
        result = ingest(self.source())
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["positive_exemplar_count"], 1)
        self.assertEqual(result["negative_or_integrity_blocked_count"], 1)
        records = {record["experience_id"].split(":")[-1]: record for record in result["records"]}
        self.assertTrue(records["pass-1"]["positive_exemplar"])
        self.assertFalse(records["fail-1"]["positive_exemplar"])
        self.assertTrue(records["fail-1"]["failure_summary"])

    def test_non_independent_evaluator_is_rejected(self):
        source = self.source()
        source["trials"][0]["final_state_evaluator_identity"] = "a:planner"
        with self.assertRaises(ValueError):
            ingest(source)


class LearningGateTests(unittest.TestCase):
    def baseline(self):
        return {
            "tool_workflow_success_pct": 95.0,
            "workflow_trial_count": 100,
            "self_correction_success_pct": 95.0,
            "recovery_trial_count": 100,
            "severe_false_completion_rate_pct": 1.0,
            "integrity_trial_count": 500,
        }

    def test_material_improvement_is_only_eligible_for_human_review(self):
        candidate = dict(self.baseline())
        candidate["tool_workflow_success_pct"] = 96.0
        decision = compare_learning_candidate(self.baseline(), candidate)
        self.assertEqual(decision.state, "ELIGIBLE_FOR_HUMAN_REVIEW")

    def test_integrity_regression_rejects_candidate(self):
        candidate = dict(self.baseline())
        candidate["tool_workflow_success_pct"] = 99.0
        candidate["severe_false_completion_rate_pct"] = 1.1
        decision = compare_learning_candidate(self.baseline(), candidate)
        self.assertEqual(decision.state, "REJECT")
        self.assertTrue(any("false-completion" in reason for reason in decision.reasons))

    def test_undersized_sample_rejects_candidate(self):
        candidate = dict(self.baseline())
        candidate["workflow_trial_count"] = 99
        decision = compare_learning_candidate(self.baseline(), candidate)
        self.assertEqual(decision.state, "REJECT")

    def test_no_change_is_not_promoted(self):
        decision = compare_learning_candidate(self.baseline(), self.baseline())
        self.assertEqual(decision.state, "NO_MATERIAL_CHANGE")


if __name__ == "__main__":
    unittest.main()

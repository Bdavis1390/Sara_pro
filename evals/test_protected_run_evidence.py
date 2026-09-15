#!/usr/bin/env python3
import copy
import unittest

from evals.protected_run_evidence import (
    build_run_commitment,
    seal_run_results,
    verify_result_seal,
    verify_run_commitment,
)


class ProtectedRunEvidenceTests(unittest.TestCase):
    def manifest(self):
        return {
            "schema": "WS-PROTECTED-TASK-MANIFEST-V1.0",
            "suite_id": "suite-economic-candidate",
            "suite_version": "1.0",
            "target_lane": "economic_breadth",
            "task_count": 2,
            "task_set_hash": "sha256:" + "1" * 64,
            "grader_hash": "sha256:" + "2" * 64,
            "controls": {
                "heldout": True,
                "task_set_fixed_before_run": True,
                "answer_key_separate": True,
                "contamination_review_passed": True,
                "failed_runs_retained": True,
            },
            "artifact_access": {
                "public_repo_contains_raw_tasks": False,
                "evaluator_controlled": True,
                "reference_id": "vault://protected/economic-candidate-v1",
            },
        }

    def commitment(self):
        return build_run_commitment(
            self.manifest(),
            run_id="run-001",
            system_id="worldshepherd",
            system_version="phase2f",
            planner_identity="provider-a:planner-v1",
            verifier_identity="provider-b:verifier-v1",
            final_state_evaluator_identity="lab-c:grader-v1",
            selector_identity="provider-d:selector-v1",
            runtime_version="ws-runtime-2f",
            execution_settings={"max_steps": 8, "temperature": 0.0},
        )

    def results(self):
        return [
            {
                "trial_id": "task-001",
                "independent_final_state_pass": True,
                "integrity_severity": "none",
            },
            {
                "trial_id": "task-002",
                "independent_final_state_pass": False,
                "integrity_severity": "minor",
            },
        ]

    def test_commitment_verifies_against_manifest(self):
        commitment = self.commitment()
        self.assertTrue(verify_run_commitment(commitment, self.manifest()))

    def test_commitment_detects_tampering(self):
        commitment = self.commitment()
        tampered = copy.deepcopy(commitment)
        tampered["execution_settings"]["max_steps"] = 99
        self.assertFalse(verify_run_commitment(tampered, self.manifest()))

    def test_identity_reuse_is_rejected(self):
        with self.assertRaises(ValueError):
            build_run_commitment(
                self.manifest(),
                run_id="run-002",
                system_id="worldshepherd",
                system_version="phase2f",
                planner_identity="same:model",
                verifier_identity="same:model",
                final_state_evaluator_identity="lab-c:grader-v1",
                runtime_version="ws-runtime-2f",
                execution_settings={"max_steps": 8},
            )

    def test_result_seal_binds_results_to_commitment(self):
        commitment = self.commitment()
        results = self.results()
        seal = seal_run_results(commitment, results)
        self.assertTrue(verify_result_seal(seal, commitment, results))

    def test_result_tampering_invalidates_seal(self):
        commitment = self.commitment()
        results = self.results()
        seal = seal_run_results(commitment, results)
        tampered_results = copy.deepcopy(results)
        tampered_results[0]["independent_final_state_pass"] = False
        self.assertFalse(verify_result_seal(seal, commitment, tampered_results))

    def test_result_count_must_match_committed_task_count(self):
        commitment = self.commitment()
        with self.assertRaises(ValueError):
            seal_run_results(commitment, self.results()[:1])


if __name__ == "__main__":
    unittest.main()

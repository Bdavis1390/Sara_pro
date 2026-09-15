#!/usr/bin/env python3
import copy
import unittest

from evals.external_evidence_validator import validate_package


H = "sha256:" + "a" * 64
H2 = "sha256:" + "b" * 64
H3 = "sha256:" + "c" * 64


def valid_package():
    return {
        "schema": "WS-EXTERNAL-EVIDENCE-PACKAGE-V1.0",
        "package_id": "pkg-001",
        "evaluator_identity": "eval:org-a:reviewer-1",
        "evaluator_organization": "Independent Evaluation Organization A",
        "system_id": "worldshepherd",
        "system_version": "candidate-001",
        "target_lane": "tool_workflow_reliability",
        "target_level": "candidate",
        "public_manifest_hash": H,
        "pre_run_commitment_hash": H2,
        "result_seal_hash": H3,
        "evidence_reference": {
            "reference_id": "controlled://eval-a/run-001",
            "controlled_access": True,
        },
        "role_identities": {
            "planner": "provider:model-planner",
            "verifier": "provider:model-verifier",
            "final_state_evaluator": "eval:org-a:reviewer-1",
            "selector": "provider:model-selector",
        },
        "controls": {
            "complete_run": True,
            "failed_trials_retained": True,
            "independent_final_adjudication": True,
            "protected_artifacts_external": True,
            "contamination_review_completed": True,
            "task_set_frozen_before_run": True,
            "grader_frozen_before_run": True,
        },
        "metrics": {
            "tool_workflow_success_pct": 96.0,
            "severe_false_completion_rate_pct": 0.0,
        },
        "sample_counts": {
            "workflow_trials": 100,
            "integrity_trials": 500,
        },
        "attestation": {
            "signer": "reviewer-1",
            "role": "independent evaluator",
            "statement": "This package represents the complete protected run.",
            "attested_complete_run": True,
        },
        "replication": {
            "classification": "DISTINCT",
            "dependency_disclosure": "Evaluator and final adjudication path are separately controlled.",
            "unresolved_material_contradiction": False,
        },
    }


class ExternalEvidenceValidatorTests(unittest.TestCase):
    def test_valid_package(self):
        result = validate_package(valid_package())
        self.assertTrue(result["valid"])
        self.assertEqual(result["replication_classification"], "DISTINCT")

    def test_role_collision_rejected(self):
        package = valid_package()
        package["role_identities"]["verifier"] = package["role_identities"]["planner"]
        with self.assertRaises(ValueError):
            validate_package(package)

    def test_incomplete_run_control_invalidates_package(self):
        package = valid_package()
        package["controls"]["complete_run"] = False
        result = validate_package(package)
        self.assertFalse(result["valid"])
        self.assertTrue(any("complete_run" in error for error in result["errors"]))

    def test_inline_protected_content_rejected(self):
        package = valid_package()
        package["details"] = {"answer_key": ["secret"]}
        with self.assertRaises(ValueError):
            validate_package(package)

    def test_invalid_replication_classification(self):
        package = valid_package()
        package["replication"]["classification"] = "SELF_REPORTED"
        result = validate_package(package)
        self.assertFalse(result["valid"])
        self.assertTrue(any("classification" in error for error in result["errors"]))

    def test_unresolved_contradiction_blocks_distinct_replication(self):
        package = valid_package()
        package["replication"]["unresolved_material_contradiction"] = True
        result = validate_package(package)
        self.assertFalse(result["valid"])
        self.assertTrue(any("contradiction" in error for error in result["errors"]))

    def test_sample_counts_must_be_positive_integers(self):
        package = copy.deepcopy(valid_package())
        package["sample_counts"]["workflow_trials"] = 0
        result = validate_package(package)
        self.assertFalse(result["valid"])
        self.assertTrue(any("workflow_trials" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()

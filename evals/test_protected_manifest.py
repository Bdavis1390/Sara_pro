#!/usr/bin/env python3
import unittest

from protected_manifest import validate_manifest


class ProtectedManifestTests(unittest.TestCase):
    def manifest(self):
        return {
            "schema": "WS-PROTECTED-TASK-MANIFEST-V1.0",
            "suite_id": "protected-workflow-candidate",
            "suite_version": "2026-09-a",
            "target_lane": "tool_workflow_reliability",
            "task_count": 100,
            "task_set_hash": "sha256:" + "a" * 64,
            "grader_hash": "sha256:" + "b" * 64,
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
                "reference_id": "private-eval-store:workflow-candidate-v1",
            },
        }

    def test_valid_hash_only_manifest_passes(self):
        result = validate_manifest(self.manifest())
        self.assertTrue(result["valid"])
        self.assertEqual(result["task_count"], 100)

    def test_inline_hidden_tasks_are_rejected(self):
        manifest = self.manifest()
        manifest["tasks"] = [{"prompt": "secret"}]
        with self.assertRaises(ValueError):
            validate_manifest(manifest)

    def test_failed_contamination_control_blocks_manifest(self):
        manifest = self.manifest()
        manifest["controls"]["contamination_review_passed"] = False
        result = validate_manifest(manifest)
        self.assertFalse(result["valid"])

    def test_non_hash_artifact_identifier_rejected(self):
        manifest = self.manifest()
        manifest["task_set_hash"] = "not-a-hash"
        with self.assertRaises(ValueError):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()

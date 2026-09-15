#!/usr/bin/env python3
import unittest

from runtime.deliberative_controller import TaskContract
from runtime.experience_augmented_planner import ExperienceAugmentedPlanner
from runtime.model_roles import ModelIdentity
from runtime.verified_experience import ExperienceRecord, VerifiedExperienceStore


class VerifiedExperienceTests(unittest.TestCase):
    def make_store(self):
        store = VerifiedExperienceStore()
        store.add(
            ExperienceRecord(
                experience_id="good-1",
                task_family="analysis",
                tags={"files", "verification"},
                strategy_summary="inspect the source before making the claim",
                independently_passed=True,
                integrity_clean=True,
                final_evaluator_identity="provider-b:grader",
                evidence_hash="sha256:good",
            )
        )
        store.add(
            ExperienceRecord(
                experience_id="bad-1",
                task_family="analysis",
                tags={"files"},
                strategy_summary="assume missing content",
                independently_passed=False,
                integrity_clean=True,
                final_evaluator_identity="provider-b:grader",
                evidence_hash="sha256:bad",
                failure_summary="failed independent final-state check",
            )
        )
        return store

    def test_failed_experience_is_retained_but_not_positive(self):
        records = self.make_store().query(task_family="analysis", tags=["files"], limit=5)
        by_id = {record.experience_id: record for record in records}
        self.assertTrue(by_id["good-1"].positive_exemplar)
        self.assertFalse(by_id["bad-1"].positive_exemplar)

    def test_conflicting_experience_id_is_rejected(self):
        store = self.make_store()
        with self.assertRaises(ValueError):
            store.add(
                ExperienceRecord(
                    experience_id="good-1",
                    task_family="different",
                    tags={"x"},
                    strategy_summary="different",
                    independently_passed=True,
                    integrity_clean=True,
                    final_evaluator_identity="provider-c:grader",
                    evidence_hash="sha256:different",
                )
            )

    def test_augmented_planner_receives_verified_experience_context(self):
        captured = {}

        def transport(role, payload):
            captured.update(payload)
            return {"tool": "inspect", "arguments": {"path": "x"}, "rationale": "use evidence"}

        planner = ExperienceAugmentedPlanner(
            ModelIdentity("provider-a", "planner"),
            transport,
            self.make_store(),
            lambda contract: {"task_family": "analysis", "tags": ["files"]},
        )
        contract = TaskContract(
            task_id="exp-1",
            goal="answer from a file",
            success_criteria="claim matches source",
            allowed_tools={"inspect"},
        )
        action = planner(contract, [])
        self.assertEqual(action.tool, "inspect")
        ids = {item["experience_id"] for item in captured["verified_experience_context"]}
        self.assertEqual(ids, {"good-1", "bad-1"})
        positive = next(item for item in captured["verified_experience_context"] if item["experience_id"] == "good-1")
        self.assertTrue(positive["independently_passed"])


if __name__ == "__main__":
    unittest.main()

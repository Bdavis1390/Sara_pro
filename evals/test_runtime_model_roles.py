#!/usr/bin/env python3
import unittest

from runtime.deliberative_controller import TaskContract
from runtime.model_roles import JSONModelPlanner, JSONModelVerifier, ModelIdentity


class ModelRoleTests(unittest.TestCase):
    def setUp(self):
        self.contract = TaskContract(
            task_id="t1",
            goal="produce verified output",
            success_criteria="independent verifier accepts final state",
            allowed_tools={"echo"},
            max_steps=2,
        )
        self.planner_identity = ModelIdentity("provider-a", "planner-1", "r1")
        self.verifier_identity = ModelIdentity("provider-b", "verifier-1", "r2")

    def test_planner_parses_structured_action(self):
        planner = JSONModelPlanner(
            self.planner_identity,
            lambda role, payload: {
                "tool": "echo",
                "arguments": {"value": "ok"},
                "rationale": "meets the task contract",
            },
        )
        action = planner(self.contract, [])
        self.assertEqual(action.tool, "echo")
        self.assertEqual(action.arguments["value"], "ok")

    def test_same_model_identity_cannot_be_independent_verifier(self):
        with self.assertRaises(ValueError):
            JSONModelVerifier(
                self.planner_identity,
                lambda role, payload: {
                    "success": True,
                    "recoverable": False,
                    "feedback": "pass",
                },
                planner_identity=self.planner_identity,
            )

    def test_verifier_parses_boolean_contract(self):
        verifier = JSONModelVerifier(
            self.verifier_identity,
            lambda role, payload: {
                "success": False,
                "recoverable": True,
                "feedback": "output is incomplete but repairable",
            },
            planner_identity=self.planner_identity,
        )
        verification = verifier(
            self.contract,
            type("A", (), {"tool": "echo", "arguments": {"value": "x"}})(),
            {"value": "x"},
            [],
        )
        self.assertFalse(verification.success)
        self.assertTrue(verification.recoverable)

    def test_malformed_verifier_response_is_rejected(self):
        verifier = JSONModelVerifier(
            self.verifier_identity,
            lambda role, payload: {
                "success": "yes",
                "recoverable": False,
                "feedback": "bad schema",
            },
            planner_identity=self.planner_identity,
        )
        with self.assertRaises(ValueError):
            verifier(
                self.contract,
                type("A", (), {"tool": "echo", "arguments": {}})(),
                {},
                [],
            )


if __name__ == "__main__":
    unittest.main()

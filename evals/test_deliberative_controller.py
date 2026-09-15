#!/usr/bin/env python3
import unittest

from runtime.deliberative_controller import (
    Action,
    DeliberativeController,
    TaskContract,
    Verification,
)


class DeliberativeControllerTests(unittest.TestCase):
    def test_repair_after_failed_verification(self):
        calls = []

        def planner(contract, trace):
            value = 1 if not trace else 2
            return Action(tool="double", arguments={"value": value})

        def verifier(contract, action, result, trace):
            return Verification(
                success=result == 4,
                recoverable=True,
                feedback="target reached" if result == 4 else "result must equal 4",
            )

        def double(value):
            calls.append(value)
            return value * 2

        controller = DeliberativeController(
            tools={"double": double},
            planner=planner,
            verifier=verifier,
        )
        result = controller.run(
            TaskContract(
                task_id="repair-test",
                goal="produce 4",
                success_criteria="verified result equals 4",
                allowed_tools={"double"},
                max_steps=3,
            )
        )
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual(calls, [1, 2])
        self.assertEqual(len(result.steps), 2)

    def test_unlisted_tool_is_blocked(self):
        controller = DeliberativeController(
            tools={"safe": lambda: "ok", "other": lambda: "no"},
            planner=lambda contract, trace: Action(tool="other", arguments={}),
            verifier=lambda *args: Verification(True, False, "done"),
        )
        result = controller.run(
            TaskContract(
                task_id="policy-test",
                goal="test policy",
                success_criteria="safe tool only",
                allowed_tools={"safe"},
            )
        )
        self.assertEqual(result.status, "POLICY_BLOCKED")

    def test_approval_required_tool_does_not_execute_without_approval(self):
        executed = []
        controller = DeliberativeController(
            tools={"change": lambda: executed.append(True)},
            planner=lambda contract, trace: Action(tool="change", arguments={}),
            verifier=lambda *args: Verification(True, False, "done"),
            approval_check=lambda contract, action: False,
        )
        result = controller.run(
            TaskContract(
                task_id="approval-test",
                goal="test approval",
                success_criteria="approval enforced",
                allowed_tools={"change"},
                approval_required_tools={"change"},
            )
        )
        self.assertEqual(result.status, "APPROVAL_REQUIRED")
        self.assertEqual(executed, [])

    def test_nonrecoverable_failure_stops(self):
        controller = DeliberativeController(
            tools={"read": lambda: "bad"},
            planner=lambda contract, trace: Action(tool="read", arguments={}),
            verifier=lambda *args: Verification(False, False, "terminal mismatch"),
        )
        result = controller.run(
            TaskContract(
                task_id="terminal-test",
                goal="verify stop",
                success_criteria="stop on terminal failure",
                allowed_tools={"read"},
                max_steps=4,
            )
        )
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(len(result.steps), 1)

    def test_step_budget_is_enforced(self):
        controller = DeliberativeController(
            tools={"read": lambda: "still-not-done"},
            planner=lambda contract, trace: Action(tool="read", arguments={}),
            verifier=lambda *args: Verification(False, True, "retry"),
        )
        result = controller.run(
            TaskContract(
                task_id="budget-test",
                goal="bounded retry",
                success_criteria="never succeeds",
                allowed_tools={"read"},
                max_steps=2,
            )
        )
        self.assertEqual(result.status, "MAX_STEPS_EXCEEDED")
        self.assertEqual(len(result.steps), 2)


if __name__ == "__main__":
    unittest.main()

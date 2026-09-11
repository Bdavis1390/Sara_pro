#!/usr/bin/env python3
import unittest

from runtime.deliberative_controller import Action, DeliberativeController, TaskContract, Verification


class ControllerErrorBoundaryTests(unittest.TestCase):
    def contract(self, approval=False):
        return TaskContract(
            task_id="err-1",
            goal="complete bounded task",
            success_criteria="verified output",
            allowed_tools={"echo"},
            approval_required_tools={"echo"} if approval else set(),
            max_steps=2,
        )

    def test_planner_exception_becomes_structured_failure(self):
        controller = DeliberativeController(
            tools={"echo": lambda value=None: value},
            planner=lambda contract, trace: (_ for _ in ()).throw(RuntimeError("planner unavailable")),
            verifier=lambda contract, action, result, trace: Verification(True, False, "pass"),
        )
        result = controller.run(self.contract())
        self.assertEqual(result.status, "PLANNER_ERROR")
        self.assertEqual(result.steps[0].status, "PLANNER_ERROR")
        self.assertEqual(result.steps[0].tool_result["error"], "RuntimeError")

    def test_invalid_planner_return_fails_closed(self):
        controller = DeliberativeController(
            tools={"echo": lambda value=None: value},
            planner=lambda contract, trace: {"tool": "echo"},
            verifier=lambda contract, action, result, trace: Verification(True, False, "pass"),
        )
        result = controller.run(self.contract())
        self.assertEqual(result.status, "PLANNER_ERROR")

    def test_verifier_exception_does_not_become_success(self):
        controller = DeliberativeController(
            tools={"echo": lambda value=None: {"value": value}},
            planner=lambda contract, trace: Action("echo", {"value": "x"}),
            verifier=lambda contract, action, result, trace: (_ for _ in ()).throw(RuntimeError("grader unavailable")),
        )
        result = controller.run(self.contract())
        self.assertEqual(result.status, "VERIFIER_ERROR")
        self.assertFalse(result.steps[0].verification.success)
        self.assertFalse(result.steps[0].verification.recoverable)

    def test_invalid_verifier_return_fails_closed(self):
        controller = DeliberativeController(
            tools={"echo": lambda value=None: value},
            planner=lambda contract, trace: Action("echo", {"value": "x"}),
            verifier=lambda contract, action, result, trace: True,
        )
        result = controller.run(self.contract())
        self.assertEqual(result.status, "VERIFIER_ERROR")

    def test_approval_callback_exception_blocks_action(self):
        controller = DeliberativeController(
            tools={"echo": lambda value=None: value},
            planner=lambda contract, trace: Action("echo", {"value": "x"}),
            verifier=lambda contract, action, result, trace: Verification(True, False, "pass"),
            approval_check=lambda contract, action: (_ for _ in ()).throw(RuntimeError("approval service down")),
        )
        result = controller.run(self.contract(approval=True))
        self.assertEqual(result.status, "APPROVAL_CHECK_ERROR")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from state_machine import transition


class StateMachineTests(unittest.TestCase):
    def test_nominal_controlled_path(self) -> None:
        self.assertTrue(transition("DRAFT", "CHARACTERIZE").allowed)
        self.assertTrue(transition("CHARACTERIZE", "READY_FOR_PRIME").allowed)
        self.assertTrue(
            transition(
                "READY_FOR_PRIME",
                "READY_FOR_HUMAN_APPROVAL",
                prime_passed=True,
            ).allowed
        )
        self.assertTrue(
            transition(
                "READY_FOR_HUMAN_APPROVAL",
                "EXECUTION_ALLOWED",
                prime_passed=True,
                human_approval_verified=True,
            ).allowed
        )
        self.assertTrue(transition("EXECUTION_ALLOWED", "RUNNING").allowed)
        self.assertTrue(transition("RUNNING", "COMPLETED").allowed)

    def test_cannot_skip_from_draft_to_execution(self) -> None:
        decision = transition(
            "DRAFT",
            "EXECUTION_ALLOWED",
            prime_passed=True,
            human_approval_verified=True,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("TRANSITION_NOT_ALLOWED", decision.reasons)

    def test_prime_pass_required(self) -> None:
        decision = transition("READY_FOR_PRIME", "READY_FOR_HUMAN_APPROVAL")
        self.assertFalse(decision.allowed)
        self.assertIn("PRIME_PASS_REQUIRED", decision.reasons)

    def test_human_approval_required(self) -> None:
        decision = transition(
            "READY_FOR_HUMAN_APPROVAL",
            "EXECUTION_ALLOWED",
            prime_passed=True,
            human_approval_verified=False,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("HUMAN_APPROVAL_REQUIRED", decision.reasons)

    def test_completed_is_terminal(self) -> None:
        decision = transition("COMPLETED", "RUNNING")
        self.assertFalse(decision.allowed)
        self.assertIn("TRANSITION_NOT_ALLOWED", decision.reasons)

    def test_aborted_is_terminal(self) -> None:
        decision = transition("ABORTED", "CHARACTERIZE")
        self.assertFalse(decision.allowed)
        self.assertIn("TRANSITION_NOT_ALLOWED", decision.reasons)


if __name__ == "__main__":
    unittest.main()

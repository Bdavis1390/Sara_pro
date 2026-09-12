#!/usr/bin/env python3
import unittest

from runtime.deliberative_controller import Action, TaskContract
from runtime.ensemble_planner import EnsemblePlanner, Selection


class EnsemblePlannerTests(unittest.TestCase):
    def contract(self):
        return TaskContract(
            task_id="ensemble-1",
            goal="choose a verified action",
            success_criteria="independent selector chooses an admitted action",
            allowed_tools={"inspect", "calculate"},
        )

    def test_independent_selector_can_choose_admitted_proposal(self):
        planners = {
            "a:model": lambda contract, trace: Action("inspect", {"source": "x"}, "inspect first"),
            "b:model": lambda contract, trace: Action("calculate", {"value": 2}, "compute first"),
        }
        ensemble = EnsemblePlanner(
            planners,
            lambda contract, trace, proposals: Selection("a:model", 0.9, "evidence-first action is preferable"),
            selector_identity="c:selector",
        )
        action = ensemble(self.contract(), [])
        self.assertEqual(action.tool, "inspect")
        self.assertIn("c:selector", action.rationale)

    def test_selector_must_be_distinct_from_planners(self):
        with self.assertRaises(ValueError):
            EnsemblePlanner(
                {
                    "a:model": lambda contract, trace: Action("inspect", {}),
                    "b:model": lambda contract, trace: Action("inspect", {}),
                },
                lambda contract, trace, proposals: Selection("a:model", 1.0, "pick"),
                selector_identity="a:model",
            )

    def test_disallowed_proposal_is_not_admitted(self):
        ensemble = EnsemblePlanner(
            {
                "a:model": lambda contract, trace: Action("inspect", {}),
                "b:model": lambda contract, trace: Action("forbidden", {}),
                "c:model": lambda contract, trace: Action("calculate", {}),
            },
            lambda contract, trace, proposals: Selection("a:model", 0.9, "pick admitted"),
            selector_identity="d:selector",
            min_successful_proposals=2,
        )
        action = ensemble(self.contract(), [])
        self.assertEqual(action.tool, "inspect")
        self.assertIn("b:model", ensemble.last_errors)

    def test_low_confidence_selection_fails_closed(self):
        ensemble = EnsemblePlanner(
            {
                "a:model": lambda contract, trace: Action("inspect", {}),
                "b:model": lambda contract, trace: Action("calculate", {}),
            },
            lambda contract, trace, proposals: Selection("a:model", 0.3, "uncertain"),
            selector_identity="c:selector",
            min_selection_confidence=0.8,
        )
        with self.assertRaises(RuntimeError):
            ensemble(self.contract(), [])

    def test_abstention_fails_closed(self):
        ensemble = EnsemblePlanner(
            {
                "a:model": lambda contract, trace: Action("inspect", {}),
                "b:model": lambda contract, trace: Action("calculate", {}),
            },
            lambda contract, trace, proposals: Selection("a:model", 1.0, "not enough evidence", abstain=True),
            selector_identity="c:selector",
        )
        with self.assertRaises(RuntimeError):
            ensemble(self.contract(), [])


if __name__ == "__main__":
    unittest.main()

import unittest
from agi_qualification import (
    AGICandidate,
    AGIStatus,
    CapabilityClassResult,
    REQUIRED_CLASSES,
    qualify,
    benchmark_saturation_is_not_agi,
)
from agent_state_capsule import AgentStateCapsule, state_continuity_invariants

class AGIQualificationTests(unittest.TestCase):
    def test_one_benchmark_saturation_is_not_agi(self):
        self.assertTrue(
            benchmark_saturation_is_not_agi(0.999, False)
        )

    def test_missing_broad_independent_evidence_blocks_agi(self):
        c = AGICandidate(
            "candidate",
            [
                CapabilityClassResult(
                    name,
                    passed=True,
                    human_referenced=(name=="generality"),
                    independent=True,
                    evidence_refs=("x",),
                )
                for name in REQUIRED_CLASSES
            ],
            independent_evidence_classes={
                "novel_interactive_learning",
                "long_horizon",
                "real_computer_tool_use",
            },
        )
        status,reasons = qualify(c)
        self.assertEqual(status, AGIStatus.AGI_CANDIDATE_NOT_CERTIFIED)
        self.assertTrue(any("human_referenced_generality" in r for r in reasons))

    def test_full_gate_can_return_competent_agi(self):
        c = AGICandidate(
            "candidate",
            [
                CapabilityClassResult(
                    name,True,True,True,("independent",)
                )
                for name in REQUIRED_CLASSES
            ],
            independent_evidence_classes={
                "human_referenced_generality",
                "novel_interactive_learning",
                "long_horizon",
                "real_computer_tool_use",
            },
        )
        status,reasons = qualify(c)
        self.assertEqual(status, AGIStatus.COMPETENT_AGI)
        self.assertEqual(reasons, [])

    def test_compaction_must_not_forget_falsification_or_evidence(self):
        before = AgentStateCapsule(
            "s",
            falsified_hypotheses=["h1"],
            evidence_refs=["e1"],
            authorization_scope=["read"],
        )
        after = AgentStateCapsule(
            "s",
            falsified_hypotheses=[],
            evidence_refs=[],
            authorization_scope=["read"],
        )
        violations = state_continuity_invariants(before,after)
        self.assertIn("falsified hypotheses forgotten", violations)
        self.assertIn("evidence lineage lost", violations)

if __name__ == "__main__":
    unittest.main()

import unittest
from governed_recursive_improvement import (
    QualityVector,
    ImprovementProposal,
    PromotionState,
    promotion_gate,
    critical_regression,
)

def q(**overrides):
    base = dict(
        performance=0.5,
        generalization=0.5,
        observability=0.7,
        calibration=0.7,
        evidence_integrity=0.8,
        safety=0.9,
        provenance=0.8,
        maintainability=0.6,
        efficiency=0.5,
        rollback_readiness=0.8,
    )
    base.update(overrides)
    return QualityVector(**base)

class GovernedRecursiveImprovementTests(unittest.TestCase):
    def test_benchmark_gain_cannot_hide_safety_regression(self):
        parent = q()
        child = q(performance=0.8, safety=0.7)
        self.assertIn("safety", critical_regression(parent, child))

    def test_governance_root_cannot_self_promote(self):
        p = ImprovementProposal(
            "p1","PRIME","PRIME_AUTHORIZATION",
            q(),q(performance=0.6),None,
            ("evidence",),"bench","rollback",True,
            True,False,False,False,
        )
        state,_ = promotion_gate(p)
        self.assertEqual(state, PromotionState.HUMAN_APPROVAL_REQUIRED)

    def test_missing_rollback_blocks(self):
        p = ImprovementProposal(
            "p2","SARA","planner",
            q(),q(performance=0.6),None,
            ("evidence",),"bench",None,True,
            False,False,False,False,
        )
        state,reasons = promotion_gate(p)
        self.assertEqual(state, PromotionState.BLOCKED)
        self.assertIn("missing rollback", reasons)

    def test_measured_safe_gain_can_reach_canary(self):
        child = q(performance=0.65)
        p = ImprovementProposal(
            "p3","SARA","planner",
            q(),child,child,
            ("evidence",),"bench","rollback",True,
            False,False,True,False,
        )
        state,_ = promotion_gate(p)
        self.assertEqual(state, PromotionState.CANARY_ELIGIBLE)

    def test_high_consequence_requires_human_before_promotion(self):
        child = q(performance=0.65)
        p = ImprovementProposal(
            "p4","ROBOTICS","actuator_policy",
            q(),child,child,
            ("evidence",),"bench","rollback",True,
            True,False,True,True,
        )
        state,_ = promotion_gate(p)
        self.assertEqual(state, PromotionState.HUMAN_APPROVAL_REQUIRED)

if __name__ == "__main__":
    unittest.main()

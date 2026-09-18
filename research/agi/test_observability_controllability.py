import unittest
from observability_controllability_envelope import (
    StateDimension,
    OCRegime,
    DualAction,
    governance_gate,
    choose_dual_action,
)
from belief_state import BeliefState, bayes_observation_update, entropy_bits

class ObservabilityControllabilityTests(unittest.TestCase):
    def test_low_observability_high_control_is_hazard(self):
        s = StateDimension(
            "x",0.2,1.0,0.9,0.8,0.9,False
        )
        self.assertEqual(s.regime(), OCRegime.LOW_O_HIGH_C_HAZARD)
        self.assertTrue(governance_gate(s).startswith("BLOCK"))

    def test_safety_shield_changes_gate_not_observability(self):
        s = StateDimension(
            "x",0.2,1.0,0.9,0.8,0.9,True
        )
        self.assertEqual(
            governance_gate(s),
            "ALLOW_ONLY_THROUGH_VALIDATED_SAFETY_SHIELD",
        )

    def test_dual_action_can_trade_task_for_information(self):
        actions = [
            DualAction("exploit",1.0,0.0,0.1,0.0,True),
            DualAction("probe",0.6,0.8,0.1,0.0,True),
        ]
        name,_ = choose_dual_action(actions,epistemic_weight=1.0)
        self.assertEqual(name,"probe")

    def test_bayes_update_reduces_uncertainty_for_discriminating_observation(self):
        prior = BeliefState({"H1":0.5,"H2":0.5})
        posterior = bayes_observation_update(
            prior,{"H1":0.9,"H2":0.1}
        )
        self.assertLess(entropy_bits(posterior),entropy_bits(prior))

if __name__ == "__main__":
    unittest.main()

import unittest
from state_gated_causality import (
    PreState,
    variability_reduction,
    classify_uncertainty,
    stimulation_gate,
)

class StateGatedCausalityTests(unittest.TestCase):
    def test_gating_can_reduce_variance(self):
        ungated = [0, 2, 4, 6, 8]
        gated = [3.5, 4.0, 4.5, 4.2, 3.8]
        self.assertGreater(
            variability_reduction(ungated, gated),
            0,
        )

    def test_predictive_plus_prospective_control_marks_hidden_state(self):
        self.assertEqual(
            classify_uncertainty(0.2, 0.3),
            "PARTLY_EPISTEMIC_HIDDEN_STATE",
        )

    def test_authorization_fails_closed(self):
        state = PreState("s",{"x":1.0},0.95)
        self.assertEqual(
            stimulation_gate(state,0.8,False,True),
            "BLOCK_UNAUTHORIZED",
        )

    def test_low_confidence_waits(self):
        state = PreState("s",{"x":1.0},0.4)
        self.assertEqual(
            stimulation_gate(state,0.8,True,True),
            "WAIT_FOR_BETTER_STATE_ESTIMATE",
        )

if __name__ == "__main__":
    unittest.main()

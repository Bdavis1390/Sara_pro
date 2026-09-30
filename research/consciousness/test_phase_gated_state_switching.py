import unittest
from phase_gated_state_switching import (
    DirectionalMode,
    NetworkPhaseState,
    PerturbationWindow,
    approximate_switch_rate_hz,
    frequency_of_switching_is_not_carrier,
)

class PhaseGatedStateSwitchingTests(unittest.TestCase):
    def test_200ms_interval_is_about_5hz_switch_rate(self):
        self.assertAlmostEqual(
            approximate_switch_rate_hz(200.0),
            5.0,
        )

    def test_numeric_match_is_not_identity(self):
        self.assertEqual(
            frequency_of_switching_is_not_carrier(5.0,5.0),
            "NUMERIC_MATCH_DOES_NOT_ESTABLISH_IDENTITY",
        )

    def test_low_confidence_state_blocks(self):
        state = NetworkPhaseState(
            1000.0,DirectionalMode.TOP_DOWN,0.5,"fc1",0.6
        )
        w = PerturbationWindow(
            state,DirectionalMode.BOTTOM_UP,0.9,"model",True
        )
        self.assertEqual(
            w.action_gate(),
            "MEASURE_STATE_FIRST",
        )

    def test_authorization_required(self):
        state = NetworkPhaseState(
            1000.0,DirectionalMode.TOP_DOWN,0.5,"fc1",0.95
        )
        w = PerturbationWindow(
            state,DirectionalMode.BOTTOM_UP,0.9,"model",False
        )
        self.assertEqual(
            w.action_gate(),
            "BLOCK_UNAUTHORIZED",
        )

if __name__ == "__main__":
    unittest.main()

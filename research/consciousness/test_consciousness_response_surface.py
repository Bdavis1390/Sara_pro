import unittest
from consciousness_response_surface import (
    EvidenceClass,
    BrainState,
    Perturbation,
    TransitionObservation,
    monotonic_activation_assumption_violated,
    fixed_frequency_is_underidentified,
    eligible_for_adaptive_control,
)

class ConsciousnessResponseSurfaceTests(unittest.TestCase):
    def test_behavior_can_improve_while_metabolism_falls(self):
        self.assertTrue(
            monotonic_activation_assumption_violated(
                consciousness_delta=2.0,
                metabolic_delta=-0.1,
            )
        )

    def test_frequency_without_state_and_geometry_is_underidentified(self):
        p = Perturbation(
            modality="SCS",
            target="cervical",
            carrier_hz=70.0,
        )
        self.assertTrue(
            fixed_frequency_is_underidentified(
                p,
                baseline_state_known=False,
            )
        )

    def test_closed_loop_fails_closed(self):
        self.assertEqual(
            eligible_for_adaptive_control(
                0.95,False,True,True
            ),
            "BLOCK_UNAUTHORIZED",
        )

    def test_low_state_confidence_requires_measurement(self):
        self.assertEqual(
            eligible_for_adaptive_control(
                0.5,True,True,True
            ),
            "MEASURE_STATE_FIRST",
        )

if __name__ == "__main__":
    unittest.main()

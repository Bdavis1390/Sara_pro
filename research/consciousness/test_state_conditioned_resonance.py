import unittest
from state_conditioned_resonance import (
    ResonanceContext,
    FrequencyProbe,
    choose_local_optimum,
    universal_frequency_claim_supported,
    context_transfer_allowed,
    adaptive_update_required,
)

class StateConditionedResonanceTests(unittest.TestCase):
    def test_local_optimum_is_context_specific(self):
        c = ResonanceContext("p1","wm_net","task_state","wm")
        probes = [
            FrequencyProbe(c,5,0.3,0.2),
            FrequencyProbe(c,10,0.8,0.6),
            FrequencyProbe(c,20,0.5,0.4),
        ]
        self.assertEqual(
            choose_local_optimum(probes).frequency_hz,
            10,
        )

    def test_different_contexts_defeat_universal_frequency(self):
        c1 = ResonanceContext("p1","x","s","t")
        c2 = ResonanceContext("p2","x","s","t")
        optima = [
            FrequencyProbe(c1,5,0.9),
            FrequencyProbe(c2,20,0.9),
        ]
        self.assertFalse(
            universal_frequency_claim_supported(optima)
        )

    def test_state_change_requires_recalibration(self):
        a = ResonanceContext("p","x","pain_free","analgesia")
        b = ResonanceContext("p","x","pain_persistent","analgesia")
        self.assertEqual(
            context_transfer_allowed(a,b),
            "RECALIBRATE_FOR_STATE",
        )

    def test_dynamic_state_requires_update(self):
        self.assertTrue(
            adaptive_update_required("state_a","state_b")
        )

if __name__ == "__main__":
    unittest.main()

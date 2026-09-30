import unittest
from network_targeted_resonance import (
    NetworkPerturbation,
    CrossFrequencyChannel,
    same_frequency_different_topology,
    claim_ceiling,
)

class NetworkTargetedResonanceTests(unittest.TestCase):
    def test_same_frequency_can_be_different_experiment(self):
        a = NetworkPerturbation("cortex","thalamus",10.0,connectivity_score=0.8)
        b = NetworkPerturbation("cortex","striatum",10.0,connectivity_score=0.4)
        self.assertTrue(same_frequency_different_topology(a,b))

    def test_frequency_without_connectivity_has_low_claim_ceiling(self):
        p = NetworkPerturbation(
            "x","y",10.0,evidence_ref="study"
        )
        self.assertEqual(
            claim_ceiling(p),
            "FREQUENCY_TARGET_ASSOCIATION_ONLY",
        )

    def test_full_network_state_is_testable(self):
        p = NetworkPerturbation(
            "cortex","thalamus",10.0,
            connectivity_score=0.8,
            criticality_score=0.7,
            evidence_ref="study",
        )
        self.assertEqual(
            claim_ceiling(p),
            "NETWORK_STATE_COUPLING_TESTABLE",
        )

    def test_cross_frequency_channel_validates(self):
        c = CrossFrequencyChannel(
            (1.0,13.0),(52.0,104.0),
            "cortex","thalamus",0.2,"awake"
        )
        c.validate()

if __name__ == "__main__":
    unittest.main()

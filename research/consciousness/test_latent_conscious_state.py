import unittest
from latent_conscious_state import (
    ConsciousnessObservable,
    EvidencePolarity,
    posterior_probability,
    negative_behavior_is_not_absence,
    theory_claim_ceiling,
)

class LatentConsciousStateTests(unittest.TestCase):
    def test_behavioral_nonresponse_with_covert_following(self):
        self.assertEqual(
            negative_behavior_is_not_absence(False, True),
            "COGNITIVE_MOTOR_DISSOCIATION_COMPATIBLE",
        )

    def test_unknown_sensitivity_nondetection_does_not_move_posterior(self):
        prior = 0.5
        obs = [
            ConsciousnessObservable(
                "test",
                EvidencePolarity.NONDETECTION,
                log_likelihood_ratio=-5.0,
                sensitivity=None,
            )
        ]
        self.assertAlmostEqual(posterior_probability(prior, obs), prior)

    def test_positive_multimodal_evidence_updates_posterior(self):
        obs = [
            ConsciousnessObservable("EEG", EvidencePolarity.SUPPORTS, 1.0),
            ConsciousnessObservable("fMRI", EvidencePolarity.SUPPORTS, 1.0),
        ]
        self.assertGreater(posterior_probability(0.2, obs), 0.2)

    def test_failed_critical_prediction_caps_theory(self):
        self.assertEqual(
            theory_claim_ceiling(2, 1),
            "THEORY_REQUIRES_REVISION_OR_NARROWING",
        )

if __name__ == "__main__":
    unittest.main()

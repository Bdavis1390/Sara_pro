import unittest
from latent_state_identifiability import (
    IdentificationProblem,
    IdentificationState,
    LatentHypothesis,
    negative_observation_claim,
)

class LatentStateIdentifiabilityTests(unittest.TestCase):
    def test_observational_equivalence_is_not_identification(self):
        h1 = LatentHypothesis(
            "H1",
            {"behavior":"none"},
            {"EEG_task":"command_pattern"},
        )
        h2 = LatentHypothesis(
            "H2",
            {"behavior":"none"},
            {"EEG_task":"no_command_pattern"},
        )
        p = IdentificationProblem(
            "conscious_state",
            [h1,h2],
            {"behavior":"none"},
            ["EEG_task"],
        )
        self.assertEqual(
            p.identification_state(),
            IdentificationState.EQUIVALENCE_CLASS_ONLY,
        )
        self.assertEqual(p.discriminating_interventions(), ["EEG_task"])

    def test_unknown_sensitivity_preserves_nondetection(self):
        self.assertEqual(
            negative_observation_claim(False, None),
            "NONDETECTION_ONLY",
        )

    def test_high_sensitivity_negative_is_evidence_not_absolute_proof(self):
        self.assertEqual(
            negative_observation_claim(False, 0.95),
            "NEGATIVE_EVIDENCE_WITH_KNOWN_SENSITIVITY",
        )

if __name__ == "__main__":
    unittest.main()

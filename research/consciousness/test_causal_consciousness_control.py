import unittest
from causal_consciousness_control import (
    EvidenceLevel,
    ValidationModality,
    MechanismPrediction,
    StimulationPattern,
    closed_loop_candidate,
)

class CausalConsciousnessControlTests(unittest.TestCase):
    def test_two_orthogonal_modalities_raise_mechanism_ceiling(self):
        p = MechanismPrediction(
            "p","mechanism","model",
            (
                ValidationModality.RNA_SEQ,
                ValidationModality.ANIMAL_MODEL,
            ),
            EvidenceLevel.ORTHOGONAL_VALIDATION,
        )
        self.assertEqual(
            p.claim_ceiling(),
            "MULTIMODAL_MECHANISM_SUPPORT",
        )

    def test_naked_frequency_is_insufficient(self):
        p = StimulationPattern("x",intraburst_hz=50.0)
        self.assertEqual(
            p.claim_ceiling(),
            "INSUFFICIENT_INTERVENTION_SPECIFICATION",
        )

    def test_pilot_randomized_is_preliminary(self):
        p = StimulationPattern(
            "pitbs",
            intraburst_hz=50.0,
            envelope_hz=5.0,
            target="left DLPFC",
            duration_s=582.0,
            evidence_level=EvidenceLevel.PILOT_RANDOMIZED,
        )
        self.assertEqual(
            p.claim_ceiling(),
            "PRELIMINARY_CAUSAL_CLINICAL_EVIDENCE",
        )

    def test_closed_loop_fails_closed(self):
        self.assertEqual(
            closed_loop_candidate(0.95,True,True,False),
            "BLOCK_UNAUTHORIZED",
        )
        self.assertEqual(
            closed_loop_candidate(0.6,True,True,True),
            "MEASURE_MORE_BEFORE_PERTURBING",
        )

if __name__ == "__main__":
    unittest.main()

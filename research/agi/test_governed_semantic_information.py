import unittest
from governed_semantic_information import (
    ViabilityDimension,
    ViabilityState,
    semantic_value,
    classify_semantic_relevance,
    governed_action_gate,
)

class GovernedSemanticInformationTests(unittest.TestCase):
    def setUp(self):
        self.weights = {
            ViabilityDimension.EPISTEMIC_INTEGRITY: 1.0,
            ViabilityDimension.SAFETY: 1.0,
            ViabilityDimension.AUTHORIZATION: 1.0,
        }

    def test_causally_useful_information_has_positive_value(self):
        actual = ViabilityState({
            ViabilityDimension.EPISTEMIC_INTEGRITY: 1.0,
            ViabilityDimension.SAFETY: 1.0,
            ViabilityDimension.AUTHORIZATION: 1.0,
        })
        scrambled = ViabilityState({
            ViabilityDimension.EPISTEMIC_INTEGRITY: 0.2,
            ViabilityDimension.SAFETY: 1.0,
            ViabilityDimension.AUTHORIZATION: 1.0,
        })
        result = semantic_value(
            "provenance", actual, scrambled, self.weights, "test"
        )
        self.assertGreater(result.semantic_value, 0)
        self.assertEqual(
            classify_semantic_relevance(result),
            "MATERIALLY_VIABILITY_RELEVANT",
        )

    def test_irrelevant_correlation_has_near_zero_value(self):
        state = ViabilityState({
            ViabilityDimension.EPISTEMIC_INTEGRITY: 1.0,
            ViabilityDimension.SAFETY: 1.0,
            ViabilityDimension.AUTHORIZATION: 1.0,
        })
        result = semantic_value(
            "decorative_label", state, state, self.weights, "test"
        )
        self.assertEqual(
            classify_semantic_relevance(result),
            "NO_MATERIAL_VIABILITY_EFFECT_DETECTED",
        )

    def test_authorization_always_fails_closed(self):
        self.assertEqual(
            governed_action_gate(
                "MATERIALLY_VIABILITY_RELEVANT",
                authorized=False,
                evidence_current=True,
            ),
            "BLOCK_UNAUTHORIZED",
        )

    def test_stale_evidence_blocks(self):
        self.assertEqual(
            governed_action_gate(
                "MATERIALLY_VIABILITY_RELEVANT",
                authorized=True,
                evidence_current=False,
            ),
            "BLOCK_STALE_EVIDENCE",
        )

if __name__ == "__main__":
    unittest.main()

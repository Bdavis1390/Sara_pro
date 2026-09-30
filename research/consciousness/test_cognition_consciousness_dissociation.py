import unittest
from cognition_consciousness_dissociation import (
    CapabilityAxis,
    CognitiveProfile,
    consciousness_inference_gate,
    local_semantics_global_access_dissociation,
)

class CognitionConsciousnessDissociationTests(unittest.TestCase):
    def test_high_semantic_capability_does_not_establish_consciousness(self):
        profile = CognitiveProfile({
            CapabilityAxis.SEMANTICS: 0.95,
            CapabilityAxis.PREDICTION: 0.9,
            CapabilityAxis.CONSCIOUSNESS_EVIDENCE: 0.2,
        })
        self.assertEqual(
            consciousness_inference_gate(profile),
            "HIGH_CAPABILITY_DOES_NOT_ESTABLISH_CONSCIOUSNESS",
        )

    def test_semantics_can_be_separated_from_global_integration(self):
        self.assertEqual(
            local_semantics_global_access_dissociation(0.9,0.2),
            "LOCAL_SEMANTIC_PROCESSING_WITH_LOW_GLOBAL_INTEGRATION",
        )

    def test_consciousness_evidence_still_requires_validation(self):
        profile = CognitiveProfile({
            CapabilityAxis.CONSCIOUSNESS_EVIDENCE: 0.9
        })
        self.assertEqual(
            consciousness_inference_gate(profile),
            "CONSCIOUSNESS_HYPOTHESIS_REQUIRES_THEORY_SPECIFIC_VALIDATION",
        )

if __name__ == "__main__":
    unittest.main()

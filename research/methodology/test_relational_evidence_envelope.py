import unittest
from relational_evidence_envelope import (
    Layer,
    RelationalEvidenceEnvelope,
    nonflattening_violation,
)

class RelationalEvidenceEnvelopeTests(unittest.TestCase):
    def test_literal_only_is_not_consequential_ready(self):
        env = RelationalEvidenceEnvelope(
            "x","text",{Layer.CONTENT:"hello"}
        )
        self.assertFalse(env.consequential_ready())
        self.assertEqual(env.claim_ceiling(), "OBSERVATION_OR_HYPOTHESIS_ONLY")

    def test_relational_context_enables_higher_gate(self):
        env = RelationalEvidenceEnvelope(
            "x",
            "dataset",
            {
                Layer.CONTENT: [1,2,3],
                Layer.RELATIONS: [],
                Layer.PROVENANCE: {"source":"instrument"},
                Layer.UNCERTAINTY: {"sigma":0.1},
                Layer.DEPENDENCIES: [],
                Layer.ALTERNATIVES: ["batch effect"],
                Layer.FALSIFIERS: ["replication fails"],
            },
        )
        self.assertTrue(env.consequential_ready())
        self.assertEqual(
            env.claim_ceiling(),
            "STRUCTURED_INTERPRETATION_NO_QUANTITATIVE_VALIDATION",
        )

    def test_representation_loss_caps_claim(self):
        env = RelationalEvidenceEnvelope(
            "x",
            "legal",
            {
                Layer.CONTENT: "summary",
                Layer.RELATIONS: [],
                Layer.PROVENANCE: {},
                Layer.UNCERTAINTY: [],
                Layer.DEPENDENCIES: [],
                Layer.ALTERNATIVES: [],
                Layer.FALSIFIERS: [],
                Layer.MEASUREMENTS: [],
            },
        )
        env.record_loss("original opinion revision state not preserved")
        self.assertEqual(
            env.claim_ceiling(),
            "VALIDATION_REQUIRED_REPRESENTATION_LOSS",
        )

    def test_undisclosed_flattening_detected(self):
        lost = nonflattening_violation(
            {Layer.CONTENT, Layer.RELATIONS, Layer.PROVENANCE},
            {Layer.CONTENT},
            {Layer.PROVENANCE},
        )
        self.assertEqual(lost, {Layer.RELATIONS})

if __name__ == "__main__":
    unittest.main()

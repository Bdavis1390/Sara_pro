import unittest
from translation_audit import (
    DifferenceClass,
    TokenAlignment,
    TranslationAudit,
    summarize,
)

class TranslationAuditTests(unittest.TestCase):
    def test_stable_audit(self):
        a = TranslationAudit("a", "w", "t")
        self.assertEqual(a.classify(), {DifferenceClass.T0_STABLE})
        self.assertEqual(a.claim_ceiling(), "CURRENTLY_STABLE_WITHIN_AUDITED_EVIDENCE")

    def test_superseded_blocks_current_use(self):
        a = TranslationAudit("a", "w", "t", superseded_readings=["line 1"])
        self.assertIn(DifferenceClass.T6_SUPERSEDED, a.classify())
        self.assertEqual(a.claim_ceiling(), "DO_NOT_USE_AS_CURRENT_WITHOUT_REVISION")

    def test_witness_dependence(self):
        a = TranslationAudit("a", "w", "t", witness_variants=["A/B disagree"])
        self.assertEqual(a.claim_ceiling(), "WITNESS_DEPENDENT_TRANSLATION")

    def test_interpolation_label(self):
        a = TranslationAudit("a", "w", "t", supplied_concepts=["unstated agent"])
        self.assertEqual(a.claim_ceiling(), "INTERPRETIVE_TRANSLATION_REQUIRES_LABEL")

    def test_vector_not_scalar(self):
        a = TranslationAudit(
            "a", "w", "t",
            alignments=[TokenAlignment("x", "word", 0.8)],
            lexical_alternatives=["x could also mean y"],
        )
        vector = a.confidence_vector()
        self.assertEqual(vector["aligned_token_count"], 1)
        self.assertEqual(vector["lexical_alternative_count"], 1)

    def test_summary(self):
        audits = [
            TranslationAudit("a", "w", "t", lexical_alternatives=["x"]),
            TranslationAudit("b", "w", "t", witness_variants=["v"]),
        ]
        out = summarize(audits)
        self.assertEqual(out["T2_LEXICAL"], 1)
        self.assertEqual(out["T4_WITNESS"], 1)

if __name__ == "__main__":
    unittest.main()

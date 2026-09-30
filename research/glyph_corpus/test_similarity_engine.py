import unittest

from similarity_engine import (
    StructuralFeatures,
    benjamini_hochberg,
    claim_ceiling,
    order_similarity,
    permutation_order_test,
    structural_match,
)


class SimilarityEngineTests(unittest.TestCase):
    def test_structural_match_perfect(self):
        score = structural_match(StructuralFeatures(1, 1, 1, 1, 1, 1, 1))
        self.assertAlmostEqual(score, 1.0)

    def test_structural_match_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            structural_match(StructuralFeatures(1.2, 1, 1, 1, 1, 1, 1))

    def test_visual_match_does_not_become_provenance(self):
        statement = claim_ceiling(structural_match_score=0.99)
        self.assertEqual(statement, "strong visual/structural correspondence")

    def test_transmission_requires_explicit_evidence_flag(self):
        statement = claim_ceiling(
            structural_match_score=0.9,
            semantic_match=True,
            chronology_contact=True,
            documented_transmission=True,
        )
        self.assertEqual(statement, "supported historical transmission")

    def test_exact_order(self):
        self.assertEqual(order_similarity(["a", "b", "c"], ["a", "b", "c"]), 1.0)

    def test_permutation_order_test_returns_valid_p(self):
        score, p_value = permutation_order_test(
            ["square", "crescent", "triangle", "hexagram", "circle"],
            ["square", "crescent", "triangle", "hexagram", "circle"],
            permutations=2000,
            seed=7,
        )
        self.assertEqual(score, 1.0)
        self.assertGreater(p_value, 0.0)
        self.assertLessEqual(p_value, 1.0)

    def test_bh_preserves_monotonic_control(self):
        adjusted = benjamini_hochberg([0.001, 0.01, 0.04, 0.2])
        self.assertEqual(len(adjusted), 4)
        self.assertTrue(all(0 <= q <= 1 for q in adjusted))
        self.assertLessEqual(adjusted[0], adjusted[1])
        self.assertLessEqual(adjusted[1], adjusted[2])
        self.assertLessEqual(adjusted[2], adjusted[3])


if __name__ == "__main__":
    unittest.main()

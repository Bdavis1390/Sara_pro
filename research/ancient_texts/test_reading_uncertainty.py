import unittest
from reading_uncertainty import (
    ReadingHypothesis,
    ReadingLattice,
    ReadingStatus,
    phonological_match_status,
    reject_naive_cognate_claim,
)

class ReadingUncertaintyTests(unittest.TestCase):
    def test_pragmatic_display_choice_caps_sound_claim(self):
        pyramid = ReadingLattice(
            lemma_id="TLA-71780",
            semantic_value="pyramid",
            display_transliteration="mr",
            corpus_pragmatic_choice=True,
            readings=[
                ReadingHypothesis("mḥr", ReadingStatus.COMPETING_PUBLISHED)
            ],
        )
        self.assertEqual(
            pyramid.claim_ceiling_for_sound_match(),
            "PHONOLOGICAL_MATCH_UNRESOLVED",
        )

    def test_alternative_reading_is_preserved(self):
        item = ReadingLattice(
            lemma_id="x",
            semantic_value="test",
            display_transliteration="tp",
            corpus_pragmatic_choice=True,
            readings=[
                ReadingHypothesis("dp", ReadingStatus.COMPETING_PUBLISHED),
                ReadingHypothesis("ḏp", ReadingStatus.HISTORICAL),
            ],
        )
        self.assertEqual(item.candidate_readings(), {"tp", "dp", "ḏp"})

    def test_surface_match_does_not_promote_cognacy(self):
        a = ReadingLattice("a", None, "mr")
        b = ReadingLattice("b", None, "mr")
        with self.assertRaises(PermissionError):
            reject_naive_cognate_claim(a, b)

    def test_overlap_with_uncertainty_is_correspondence_only(self):
        a = ReadingLattice(
            "a", None, "Wsjr", True,
            [ReadingHypothesis("Js-jr(j)", ReadingStatus.COMPETING_PUBLISHED)],
        )
        b = ReadingLattice("b", None, "Js-jr(j)")
        status = phonological_match_status(a, b)
        self.assertTrue(status["match"])
        self.assertEqual(
            status["claim_ceiling"],
            "CORRESPONDENCE_ONLY_READING_UNCERTAIN",
        )

if __name__ == "__main__":
    unittest.main()

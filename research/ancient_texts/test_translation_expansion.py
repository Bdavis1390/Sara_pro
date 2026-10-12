import unittest
from translation_source_watch import (
    WatchSeverity,
    damos_note_signals,
    tla_editorial_state_signal,
    gandhari_revision_signal,
    undeciphered_translation_signal,
)
from translation_integrity_vector import TranslationIntegrityVector

class TranslationExpansionTests(unittest.TestCase):
    def test_damos_new_reading_triggers_reaudit(self):
        signals = damos_note_signals("PY-X", "READ€ source of new/different reading")
        self.assertTrue(any(s.severity == WatchSeverity.REAUDIT for s in signals))

    def test_tla_verification_pending_caps_confidence(self):
        signal = tla_editorial_state_signal("d11", "Verification pending")
        self.assertEqual(signal.severity, WatchSeverity.REVIEW)

    def test_gandhari_reading_change_triggers_reaudit(self):
        signals = gandhari_revision_signal("CKI-1", True, False)
        self.assertEqual(signals[0].severity, WatchSeverity.REAUDIT)

    def test_undeciphered_running_translation_blocks(self):
        signal = undeciphered_translation_signal(
            "Linear A","HT13",True,False
        )
        self.assertEqual(signal.severity, WatchSeverity.BLOCK)

    def test_uncertainty_flattening_caps_translation(self):
        v = TranslationIntegrityVector(
            source_items=10,
            aligned_items=10,
            uncertainty_markers_source=3,
            uncertainty_markers_preserved=1,
        )
        self.assertEqual(
            v.claim_ceiling(),
            "UNCERTAINTY_FLATTENED_REQUIRES_REVIEW",
        )

    def test_no_single_score_vector(self):
        v = TranslationIntegrityVector(source_items=2, aligned_items=2)
        out = v.vector()
        self.assertIn("alignment_coverage", out)
        self.assertIn("unsupported_insertions", out)

if __name__ == "__main__":
    unittest.main()

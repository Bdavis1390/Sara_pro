import unittest
from layer_version_skew import (
    LayerVersion,
    check_dependency,
    named_entity_mismatch,
    publication_state,
)

class LayerVersionSkewTests(unittest.TestCase):
    def test_unpinned_translation_fails_closed(self):
        source = LayerVersion("transcription", "Ἱππόνικος")
        translation = LayerVersion("translation", "Hippolitos to Akousilaos")
        status = check_dependency(source, translation)
        self.assertTrue(status.stale)
        self.assertEqual(status.reason, "DOWNSTREAM_DEPENDENCY_UNPINNED")

    def test_changed_upstream_marks_stale(self):
        old = LayerVersion("old", "Ἱππόλιτος")
        new = LayerVersion("new", "Ἱππόνικος")
        translation = LayerVersion(
            "translation",
            "Hippolitos to Akousilaos",
            depends_on_hash=old.content_hash,
        )
        status = check_dependency(new, translation)
        self.assertTrue(status.stale)
        self.assertEqual(status.reason, "UPSTREAM_CONTENT_CHANGED")

    def test_named_entity_mismatch_is_material(self):
        check = named_entity_mismatch({"Hipponikos", "Akousilaos"}, {"Hippolitos", "Akousilaos"})
        self.assertTrue(check["material_mismatch"])
        self.assertIn("Hipponikos", check["missing_current_entities"])
        self.assertIn("Hippolitos", check["legacy_or_extra_entities"])

    def test_case_is_stale_pending_reaudit(self):
        source = LayerVersion("transcription", "Ἱππόνικος")
        translation = LayerVersion("translation", "Hippolitos to Akousilaos")
        dep = check_dependency(source, translation)
        entities = named_entity_mismatch({"Hipponikos"}, {"Hippolitos"})
        self.assertEqual(publication_state(dep, entities), "STALE_PENDING_REAUDIT")

if __name__ == "__main__":
    unittest.main()

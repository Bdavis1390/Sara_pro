import unittest
from textual_identity_graph import (
    TextObject,
    TextObjectKind,
    TextualIdentityGraph,
)

class TextualIdentityGraphTests(unittest.TestCase):
    def test_same_title_family_does_not_force_identity(self):
        g = TextualIdentityGraph()
        g.add_object(TextObject(
            "aramaic","1 Enoch",TextObjectKind.PHYSICAL_WITNESS,
            language="Aramaic",physical=True
        ))
        g.add_object(TextObject(
            "ethiopic","1 Enoch",TextObjectKind.CANONICAL_COLLECTION,
            language="Ge'ez",physical=False
        ))
        self.assertFalse(g.same_translation_target("aramaic","ethiopic"))

    def test_composite_requires_label(self):
        g = TextualIdentityGraph()
        g.add_object(TextObject(
            "critical","1 Enoch",TextObjectKind.SCHOLARLY_COMPOSITE,
            language="English",
            physical=False,
            source_witnesses=("Aramaic","Greek","Ethiopic"),
        ))
        self.assertTrue(g.requires_identity_label("critical"))
        self.assertEqual(
            g.translation_target_claim("critical"),
            "TRANSLATION_TARGET_MUST_BE_EXPLICITLY_LABELED",
        )

    def test_physical_witness_can_be_explicit_target(self):
        g = TextualIdentityGraph()
        g.add_object(TextObject(
            "4Q212","1 Enoch",TextObjectKind.PHYSICAL_WITNESS,
            language="Aramaic",physical=True
        ))
        self.assertEqual(
            g.translation_target_claim("4Q212"),
            "PHYSICAL_WITNESS_TARGET_EXPLICIT",
        )

if __name__ == "__main__":
    unittest.main()

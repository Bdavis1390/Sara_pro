import unittest
from translation_lineage_graph import (
    LayerKind,
    LayerState,
    TranslationLayer,
    TranslationDependency,
    TranslationLineageGraph,
)
from oracc_translation_adapter import (
    TranslationTokenState,
    translation_available,
    parse_oracc_translation_markup,
    assert_translation_not_inferred_from_corpusjson,
)
from tei_critical_apparatus import parse_tei_apparatus, apparatus_requires_translation_review

class TranslationProgramTests(unittest.TestCase):
    def test_upstream_change_invalidates_translation(self):
        g = TranslationLineageGraph()
        src = TranslationLayer("src", LayerKind.DIPLOMATIC, "old")
        tr = TranslationLayer("tr", LayerKind.TRANSLATION, "English")
        g.add_layer(src); g.add_layer(tr)
        g.add_dependency(TranslationDependency(
            "src","tr",True,src.fingerprint
        ))
        src.content = "new"
        self.assertEqual(g.translation_claim_ceiling("tr"), "STALE_PENDING_REAUDIT")

    def test_oracc_translation_availability_separate_from_corpusjson(self):
        metadata = {"formats":{"tr-en":["P1"],"lem":["P1"]}}
        self.assertTrue(translation_available(metadata,"P1"))
        with self.assertRaises(ValueError):
            assert_translation_not_inferred_from_corpusjson(
                metadata,"P1",{"cdl":[]}
            )

    def test_oracc_uncertainty_markup_preserved(self):
        spans = parse_oracc_translation_markup(
            "He (Gudea) built @?the temple?@ [...] ..."
        )
        states = {s.state for s in spans}
        self.assertIn(TranslationTokenState.SUPPLIED, states)
        self.assertIn(TranslationTokenState.UNCERTAIN, states)
        self.assertIn(TranslationTokenState.BROKEN_OR_RESTORED, states)
        self.assertIn(TranslationTokenState.UNTRANSLATABLE, states)

    def test_tei_multiple_witness_readings_trigger_review(self):
        xml = """<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><p>
        <app xml:id="a1"><lem>alpha</lem>
        <rdg wit="#A">alpha</rdg><rdg wit="#B" cert="low">beta</rdg></app>
        </p></body></text></TEI>"""
        readings = parse_tei_apparatus(xml)
        self.assertEqual(len(readings), 2)
        self.assertTrue(apparatus_requires_translation_review(readings))

if __name__ == "__main__":
    unittest.main()

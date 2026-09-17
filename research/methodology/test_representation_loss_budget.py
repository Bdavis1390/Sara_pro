import unittest
from representation_loss_budget import (
    LayerDisposition,
    Preservation,
    RepresentationTransform,
    compose,
)

class RepresentationLossBudgetTests(unittest.TestCase):
    def test_lost_required_layer_blocks_claim(self):
        t = RepresentationTransform(
            "image-caption","image","caption",False,
            [
                LayerDisposition("objects", Preservation.APPROXIMATED),
                LayerDisposition("topology", Preservation.DISCARDED),
            ],
        )
        gate = t.claim_gate({"topology"})
        self.assertFalse(gate["allowed"])
        self.assertEqual(gate["state"], "RETURN_TO_SOURCE_OR_CAP_CLAIM")

    def test_approximate_layer_allows_with_uncertainty(self):
        t = RepresentationTransform(
            "audio-text","audio","text",False,
            [LayerDisposition("lexical", Preservation.APPROXIMATED)],
        )
        self.assertEqual(
            t.claim_gate({"lexical"})["state"],
            "ALLOW_WITH_UNCERTAINTY",
        )

    def test_external_addition_requires_provenance(self):
        t = RepresentationTransform(
            "annotate","raw","annotated",False,
            [LayerDisposition("diagnosis", Preservation.ADDED_EXTERNAL)],
        )
        with self.assertRaises(ValueError):
            t.validate()

    def test_composed_loss_persists(self):
        a = RepresentationTransform(
            "raw-summary","raw","summary",False,
            [LayerDisposition("timing", Preservation.DISCARDED)],
        )
        b = RepresentationTransform(
            "summary-report","summary","report",False,
            [LayerDisposition("timing", Preservation.PRESERVED)],
        )
        c = compose(a,b)
        self.assertIn("timing", c.lost_layers())

if __name__ == "__main__":
    unittest.main()

import unittest
from physical_semantic_chain import (
    PSECStage,
    StageArtifact,
    PhysicalSemanticChain,
    translation_requires_material_trace,
    propagate_uncertainty,
)

class PhysicalSemanticChainTests(unittest.TestCase):
    def test_upstream_revision_has_downstream_blast_radius(self):
        chain = PhysicalSemanticChain()
        scan = StageArtifact("scan",PSECStage.TOMOGRAPHY,"scan.bin")
        ink = StageArtifact("ink",PSECStage.INK_DETECTION,"ink.npy")
        tr = StageArtifact("tr",PSECStage.TRANSCRIPTION,"greek.txt")
        en = StageArtifact("en",PSECStage.TRANSLATION,"english.txt")
        for node in [scan,ink,tr,en]:
            chain.add(node)
        chain.link("scan","ink")
        chain.link("ink","tr")
        chain.link("tr","en")
        self.assertEqual(
            set(chain.invalidate_from("scan")),
            {"ink","tr","en"},
        )

    def test_untraced_translation_blocks(self):
        t = StageArtifact("t",PSECStage.TRANSLATION,"english.txt")
        self.assertEqual(
            translation_requires_material_trace(t),
            "BLOCK_UNTRACED_TRANSLATION",
        )

    def test_traced_translation_allowed_to_review(self):
        t = StageArtifact(
            "t",PSECStage.TRANSLATION,"english.txt",
            parent_fingerprints=("abc",)
        )
        self.assertEqual(
            translation_requires_material_trace(t),
            "TRANSLATION_TRACE_PRESENT",
        )

    def test_uncertainty_accumulates_conservatively(self):
        value = propagate_uncertainty([0.1,0.2])
        self.assertAlmostEqual(value,0.28)

if __name__ == "__main__":
    unittest.main()

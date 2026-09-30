import unittest
from evidence_bom import (
    EvidenceBOM,
    EvidenceNode,
    DependencyEdge,
    NodeKind,
    Validity,
)

class EvidenceBOMTests(unittest.TestCase):
    def test_transitive_invalidation(self):
        bom = EvidenceBOM()
        for node in [
            EvidenceNode("source", NodeKind.EVIDENCE, "a", domain="science"),
            EvidenceNode("analysis", NodeKind.INTERPRETATION, "b", domain="science"),
            EvidenceNode("claim", NodeKind.CLAIM, "c", domain="science"),
        ]:
            bom.add_node(node)
        bom.add_dependency(DependencyEdge("source", "analysis", material=True))
        bom.add_dependency(DependencyEdge("analysis", "claim", material=True))
        invalidated = bom.update_fingerprint("source", "a2")
        self.assertEqual(set(invalidated), {"analysis", "claim"})
        self.assertEqual(bom.nodes["claim"].validity, Validity.REVALIDATION_REQUIRED)

    def test_nonmaterial_edge_does_not_invalidate(self):
        bom = EvidenceBOM()
        bom.add_node(EvidenceNode("source", NodeKind.EVIDENCE, "a"))
        bom.add_node(EvidenceNode("context", NodeKind.CLAIM, "b"))
        bom.add_dependency(DependencyEdge("source", "context", material=False))
        self.assertEqual(bom.update_fingerprint("source", "a2"), [])
        self.assertEqual(bom.nodes["context"].validity, Validity.CURRENT)

    def test_cycle_rejected(self):
        bom = EvidenceBOM()
        bom.add_node(EvidenceNode("a", NodeKind.EVIDENCE, "1"))
        bom.add_node(EvidenceNode("b", NodeKind.CLAIM, "2"))
        bom.add_dependency(DependencyEdge("a", "b"))
        with self.assertRaises(ValueError):
            bom.add_dependency(DependencyEdge("b", "a"))

    def test_blast_radius_by_domain(self):
        bom = EvidenceBOM()
        bom.add_node(EvidenceNode("source", NodeKind.EVIDENCE, "1", domain="medical"))
        bom.add_node(EvidenceNode("interpretation", NodeKind.INTERPRETATION, "2", domain="medical"))
        bom.add_node(EvidenceNode("decision", NodeKind.DECISION_SUPPORT, "3", domain="operations"))
        bom.add_dependency(DependencyEdge("source", "interpretation"))
        bom.add_dependency(DependencyEdge("interpretation", "decision"))
        radius = bom.blast_radius("source")
        self.assertEqual(radius["count"], 2)
        self.assertEqual(radius["by_domain"]["medical"], 1)
        self.assertEqual(radius["by_domain"]["operations"], 1)

if __name__ == "__main__":
    unittest.main()

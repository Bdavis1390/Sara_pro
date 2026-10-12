import unittest

from atip_harness import (
    BenchmarkMeta,
    shannon_entropy,
    positional_profile,
    shuffle_surrogate,
    markov_surrogate,
    claim_ceiling,
    assert_translation_permitted,
)
from evidence_graph import EvidenceGraph, Node, Edge

class HarnessTests(unittest.TestCase):
    def test_entropy(self):
        self.assertEqual(shannon_entropy(["a", "a", "a"]), 0.0)
        self.assertAlmostEqual(shannon_entropy(["a", "b"]), 1.0)

    def test_positional_profile(self):
        profile = positional_profile([["x", "a"], ["x", "b"], ["c", "x"]])
        self.assertAlmostEqual(profile["x"]["initial"], 2/3)
        self.assertAlmostEqual(profile["x"]["final"], 1/3)

    def test_surrogates_are_deterministic(self):
        src = ["a", "b", "c", "a", "b", "d"]
        self.assertEqual(shuffle_surrogate(src, 7), shuffle_surrogate(src, 7))
        self.assertEqual(markov_surrogate(src, 7), markov_surrogate(src, 7))

    def test_undeciphered_translation_block(self):
        meta = BenchmarkMeta(
            "negative-control",
            "UNDECIPHERED",
            "C0_SESSION_BLIND",
            "witness-001",
        )
        self.assertEqual(claim_ceiling(meta), "STRUCTURE_ONLY_NO_TRANSLATION")
        with self.assertRaises(PermissionError):
            assert_translation_permitted(meta)

    def test_exposure_label_mismatch_rejected(self):
        meta = BenchmarkMeta(
            "bad-label",
            "KNOWN_DECIPHERED",
            "C0_SESSION_BLIND",
            "witness-002",
            target_translation_exposed=True,
        )
        with self.assertRaises(ValueError):
            meta.validate()

class GraphTests(unittest.TestCase):
    def test_resemblance_only_stays_hypothesis(self):
        graph = EvidenceGraph()
        graph.add_node(Node("a", "Motif"))
        graph.add_node(Node("b", "Motif"))
        graph.add_edge(Edge("a", "b", "RESEMBLES"))
        self.assertEqual(
            graph.claim_ceiling("a"),
            "HYPOTHESIS_OR_STRUCTURAL_CORRESPONDENCE",
        )

    def test_translation_requires_source_evidence(self):
        graph = EvidenceGraph()
        graph.add_node(Node("token", "Token"))
        graph.add_node(Node("translation", "Translation"))
        with self.assertRaises(ValueError):
            graph.add_edge(Edge("token", "translation", "TRANSLATED_AS"))

    def test_measurement_requires_uncertainty(self):
        graph = EvidenceGraph()
        with self.assertRaises(ValueError):
            graph.add_node(Node("m", "Measurement", {"value": 1.0, "unit": "Hz"}))

    def test_valid_measurement_does_not_imply_causation(self):
        graph = EvidenceGraph()
        graph.add_node(Node("motif", "Motif"))
        graph.add_node(Node(
            "measure",
            "Measurement",
            {"value": 1.0, "unit": "Hz", "uncertainty": 0.1},
        ))
        graph.add_edge(Edge("motif", "measure", "MEASURED_AS"))
        self.assertEqual(graph.claim_ceiling("motif"), "MEASURED_RELATION_ONLY")

if __name__ == "__main__":
    unittest.main()

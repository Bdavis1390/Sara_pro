import hashlib
import unittest

from ws_cae.continuity_transparency import checkpoint, inclusion_proof, root_hash, verify_inclusion


def cid(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


class ContinuityTransparencyTests(unittest.TestCase):
    def test_all_inclusion_positions_for_uneven_sizes(self):
        for size in range(1, 10):
            values = tuple(cid(f"leaf-{i}") for i in range(size))
            for index in range(size):
                with self.subTest(size=size, index=index):
                    proof = inclusion_proof(values, index)
                    self.assertTrue(verify_inclusion(proof))
                    self.assertEqual(proof.root, root_hash(values))

    def test_order_changes_root(self):
        a, b = cid("a"), cid("b")
        self.assertNotEqual(root_hash((a, b)), root_hash((b, a)))

    def test_tampered_leaf_fails(self):
        values = tuple(cid(f"leaf-{i}") for i in range(5))
        proof = inclusion_proof(values, 2)
        tampered = proof.__class__(proof.tree_size, proof.leaf_index, cid("other"), proof.root, proof.audit_path)
        self.assertFalse(verify_inclusion(tampered))

    def test_tampered_path_fails(self):
        values = tuple(cid(f"leaf-{i}") for i in range(5))
        proof = inclusion_proof(values, 4)
        path = list(proof.audit_path)
        path[0] = cid("wrong-sibling")
        tampered = proof.__class__(proof.tree_size, proof.leaf_index, proof.content_id, proof.root, tuple(path))
        self.assertFalse(verify_inclusion(tampered))

    def test_checkpoint_is_explicit(self):
        values = (cid("a"), cid("b"), cid("c"))
        cp = checkpoint(values)
        self.assertEqual(cp["tree_size"], 3)
        self.assertEqual(cp["root_hash"], root_hash(values))
        self.assertEqual(cp["leaf_domain_separator"], "00")
        self.assertEqual(cp["node_domain_separator"], "01")


if __name__ == "__main__":
    unittest.main()

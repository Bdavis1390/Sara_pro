import hashlib
import unittest

from ws_cae.continuity_checkpoint import LinkedCheckpoint, make_checkpoint
from ws_cae.continuity_checkpoint_scitt import build_checkpoint_statement


def cid(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


class ContinuityCheckpointScittTests(unittest.TestCase):
    def test_linked_checkpoint_is_preserved(self):
        old = (cid("a"), cid("b"))
        new = old + (cid("c"),)
        cp = make_checkpoint(new, old)
        statement = build_checkpoint_statement(cp, "did:web:example.invalid", "2026-09-13T22:30:00Z")
        self.assertEqual(statement["checkpoint"]["root_hash"], cp.root_hash)
        self.assertEqual(statement["checkpoint"]["previous_root_hash"], cp.previous_root_hash)
        self.assertEqual(statement["checkpoint"]["tree_size"], 3)
        self.assertEqual(statement["checkpoint"]["previous_tree_size"], 2)

    def test_partial_predecessor_metadata_is_rejected(self):
        cp = LinkedCheckpoint(2, cid("root"), previous_tree_size=1, previous_root_hash=None)
        with self.assertRaises(ValueError):
            build_checkpoint_statement(cp, "did:web:example.invalid")

    def test_empty_issuer_is_rejected(self):
        cp = make_checkpoint((cid("a"),))
        with self.assertRaises(ValueError):
            build_checkpoint_statement(cp, " ")


if __name__ == "__main__":
    unittest.main()

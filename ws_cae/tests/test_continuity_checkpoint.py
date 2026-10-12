import hashlib
import unittest

from ws_cae.continuity_checkpoint import make_checkpoint, verify_extension


def cid(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


class ContinuityCheckpointTests(unittest.TestCase):
    def test_valid_prefix_extension(self):
        old = (cid("a"), cid("b"))
        new = old + (cid("c"), cid("d"))
        cp = make_checkpoint(new, old)
        self.assertTrue(verify_extension(cp, new, old))
        self.assertEqual(cp.previous_tree_size, 2)
        self.assertEqual(cp.tree_size, 4)

    def test_rewrite_is_rejected(self):
        old = (cid("a"), cid("b"))
        rewritten = (cid("a"), cid("x"), cid("c"))
        with self.assertRaises(ValueError):
            make_checkpoint(rewritten, old)

    def test_wrong_history_fails_verification(self):
        old = (cid("a"), cid("b"))
        new = old + (cid("c"),)
        cp = make_checkpoint(new, old)
        wrong = (cid("a"), cid("x"))
        self.assertFalse(verify_extension(cp, new, wrong))

    def test_genesis_checkpoint(self):
        values = (cid("a"),)
        cp = make_checkpoint(values)
        self.assertTrue(verify_extension(cp, values))
        self.assertIsNone(cp.previous_root_hash)


if __name__ == "__main__":
    unittest.main()

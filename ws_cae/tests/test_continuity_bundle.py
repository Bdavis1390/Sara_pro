import hashlib
import unittest

from ws_cae.continuity_bundle import build_bundle, verify_bundle
from ws_cae.continuity_checkpoint import make_checkpoint
from ws_cae.continuity_transparency import inclusion_proof


def cid(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


class ContinuityBundleTests(unittest.TestCase):
    def test_bundle_verifies(self):
        values = tuple(cid(value) for value in ("a", "b", "c", "d", "e"))
        old = values[:3]
        cp = make_checkpoint(values, old)
        proof = inclusion_proof(values, 4)
        bundle = build_bundle(content_id=values[4], inclusion=proof, checkpoint=cp)
        self.assertTrue(verify_bundle(bundle))
        self.assertEqual(bundle["checkpoint"]["previous_tree_size"], 3)

    def test_tampered_bundle_fails(self):
        values = tuple(cid(value) for value in ("a", "b", "c"))
        cp = make_checkpoint(values)
        proof = inclusion_proof(values, 1)
        bundle = build_bundle(content_id=values[1], inclusion=proof, checkpoint=cp)
        bundle["inclusion_proof"]["content_id"] = cid("wrong")
        self.assertFalse(verify_bundle(bundle))

    def test_mismatched_checkpoint_is_rejected(self):
        values = tuple(cid(value) for value in ("a", "b", "c"))
        proof = inclusion_proof(values, 0)
        wrong_cp = make_checkpoint(values[:2])
        with self.assertRaises(ValueError):
            build_bundle(content_id=values[0], inclusion=proof, checkpoint=wrong_cp)


if __name__ == "__main__":
    unittest.main()

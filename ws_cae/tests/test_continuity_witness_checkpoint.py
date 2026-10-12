import hashlib
import unittest

from ws_cae.continuity_checkpoint import LinkedCheckpoint
from ws_cae.continuity_witness import WitnessReceipt
from ws_cae.continuity_witness_checkpoint import (
    build_witnessed_checkpoint,
    verify_witnessed_checkpoint,
)


def cid(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def receipt(issuer: str, root: str, size: int = 4) -> WitnessReceipt:
    return WitnessReceipt(
        issuer=issuer,
        tree_size=size,
        root_hash=root,
        observed_at="2026-09-14T00:15:00Z",
        verification_method="EXTERNAL_TEST_VERIFIER",
        receipt_ref=f"urn:test-receipt:{issuer}:{root[-8:]}",
    )


class ContinuityWitnessCheckpointTests(unittest.TestCase):
    def test_threshold_satisfied_with_distinct_witnesses(self):
        root = cid("root")
        checkpoint = LinkedCheckpoint(4, root)
        envelope = build_witnessed_checkpoint(
            checkpoint,
            (receipt("w1", root), receipt("w2", root), receipt("w3", root)),
            threshold=2,
        )
        self.assertEqual(envelope["assessment_state"], "WITNESS_METADATA_THRESHOLD_SATISFIED")
        self.assertEqual(envelope["distinct_agreeing_witness_count"], 3)
        self.assertTrue(verify_witnessed_checkpoint(envelope))

    def test_threshold_failure_is_preserved_not_promoted(self):
        root = cid("root")
        checkpoint = LinkedCheckpoint(4, root)
        envelope = build_witnessed_checkpoint(
            checkpoint,
            (receipt("w1", root),),
            threshold=2,
        )
        self.assertEqual(envelope["assessment_state"], "WITNESS_METADATA_THRESHOLD_NOT_SATISFIED")
        self.assertFalse(envelope["equivocation_issuers"])
        self.assertTrue(verify_witnessed_checkpoint(envelope))

    def test_equivocating_witness_is_not_counted(self):
        root = cid("root")
        other = cid("other")
        checkpoint = LinkedCheckpoint(4, root)
        envelope = build_witnessed_checkpoint(
            checkpoint,
            (receipt("w1", root), receipt("w1", other), receipt("w2", root)),
            threshold=2,
        )
        self.assertEqual(envelope["assessment_state"], "WITNESS_METADATA_THRESHOLD_NOT_SATISFIED")
        self.assertEqual(envelope["equivocation_issuers"], ["w1"])
        self.assertEqual(envelope["agreeing_issuers"], ["w2"])
        self.assertTrue(verify_witnessed_checkpoint(envelope))

    def test_receipt_order_does_not_change_content_id(self):
        root = cid("root")
        checkpoint = LinkedCheckpoint(4, root)
        a = receipt("w1", root)
        b = receipt("w2", root)
        left = build_witnessed_checkpoint(checkpoint, (a, b), threshold=2)
        right = build_witnessed_checkpoint(checkpoint, (b, a), threshold=2)
        self.assertEqual(left["content_id"], right["content_id"])
        self.assertEqual(left, right)

    def test_tampering_breaks_verification(self):
        root = cid("root")
        checkpoint = LinkedCheckpoint(4, root)
        envelope = build_witnessed_checkpoint(checkpoint, (receipt("w1", root),), threshold=1)
        envelope["threshold"] = 2
        self.assertFalse(verify_witnessed_checkpoint(envelope))

    def test_malformed_checkpoint_root_fails_closed(self):
        with self.assertRaises(ValueError):
            build_witnessed_checkpoint(
                LinkedCheckpoint(4, "sha256:1234"),
                tuple(),
                threshold=1,
            )


if __name__ == "__main__":
    unittest.main()

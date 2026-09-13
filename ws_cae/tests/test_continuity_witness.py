import unittest

from ws_cae.continuity_witness import WitnessReceipt, assess_witnesses, detect_equivocation

ROOT = "sha256:" + "11" * 32
OTHER = "sha256:" + "22" * 32


def receipt(issuer: str, root: str = ROOT, size: int = 4) -> WitnessReceipt:
    return WitnessReceipt(
        issuer=issuer,
        tree_size=size,
        root_hash=root,
        observed_at="2026-09-13T22:45:00Z",
        verification_method="SCITT_OR_SIGSTORE",
        receipt_ref=f"urn:receipt:{issuer}:{root[-8:]}",
    )


class ContinuityWitnessTests(unittest.TestCase):
    def test_distinct_witness_threshold_passes(self):
        receipts = (receipt("w1"), receipt("w2"), receipt("w3"))
        result = assess_witnesses(receipts, expected_tree_size=4, expected_root_hash=ROOT, threshold=2)
        self.assertTrue(result.passed)
        self.assertEqual(result.agreeing_issuers, ("w1", "w2", "w3"))

    def test_duplicate_issuer_does_not_inflate_threshold(self):
        receipts = (receipt("w1"), receipt("w1"))
        result = assess_witnesses(receipts, expected_tree_size=4, expected_root_hash=ROOT, threshold=2)
        self.assertFalse(result.passed)
        self.assertEqual(result.agreeing_issuers, ("w1",))

    def test_equivocation_is_detected_and_rejected(self):
        receipts = (receipt("w1", ROOT), receipt("w1", OTHER), receipt("w2", ROOT))
        self.assertEqual(detect_equivocation(receipts), ("w1",))
        result = assess_witnesses(receipts, expected_tree_size=4, expected_root_hash=ROOT, threshold=2)
        self.assertFalse(result.passed)
        self.assertEqual(result.equivocation_issuers, ("w1",))
        self.assertEqual(result.agreeing_issuers, ("w2",))

    def test_wrong_root_and_size_are_rejected(self):
        receipts = (receipt("w1", OTHER), receipt("w2", ROOT, 5))
        result = assess_witnesses(receipts, expected_tree_size=4, expected_root_hash=ROOT, threshold=1)
        self.assertFalse(result.passed)
        self.assertEqual(result.agreeing_issuers, tuple())


if __name__ == "__main__":
    unittest.main()

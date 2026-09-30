from __future__ import annotations

import unittest

from worldshepherd_qcrypto_kms.p2mr_draft import (
    P2MrDraftError,
    P2MrLeaf,
    build_balanced_merkle_root,
    encode_segwit_v2_bech32m,
    experimental_p2mr_address,
    p2mr_control_block,
    p2mr_script_pubkey,
    tapbranch_hash,
    tapleaf_hash,
    verify_p2mr_merkle_path,
)


class P2MrDraftTests(unittest.TestCase):
    def test_official_bip360_single_leaf_vector(self):
        script = bytes.fromhex("20b617298552a72ade070667e86ca63b8f5789a9fe8731ef91202a91c9f3459007ac")
        expected_root = bytes.fromhex("c525714a7f49c28aedbbba78c005931a81c234b2f6c99a73e4d06082adc8bf2b")
        root = tapleaf_hash(script, 0xC0)
        self.assertEqual(root, expected_root)
        self.assertEqual(
            p2mr_script_pubkey(root).hex(),
            "5220c525714a7f49c28aedbbba78c005931a81c234b2f6c99a73e4d06082adc8bf2b",
        )
        self.assertEqual(
            encode_segwit_v2_bech32m("bc", root),
            "bc1zc5jhzjnlf8pg4mdmhfuvqpvnr2quyd9j7mye5uly6psg9twghu4ssr0v9k",
        )

    def test_high_level_builder_refuses_depth_zero_anyone_can_spend(self):
        leaf = P2MrLeaf(b"\x51")
        with self.assertRaises(P2MrDraftError):
            build_balanced_merkle_root([leaf])
        root = build_balanced_merkle_root([leaf], allow_single_leaf_test_vector=True)
        self.assertEqual(len(root), 32)

    def test_experimental_address_refuses_mainnet(self):
        root = bytes.fromhex("11" * 32)
        with self.assertRaises(P2MrDraftError):
            experimental_p2mr_address(root, network="MAINNET")
        self.assertTrue(experimental_p2mr_address(root, network="SIGNET").startswith("tb1z"))

    def test_depth_one_control_block_and_merkle_proof(self):
        left = P2MrLeaf(b"\x51")
        right = P2MrLeaf(b"\x52")
        root = tapbranch_hash(left.hash, right.hash)
        control = p2mr_control_block(left.leaf_version, [right.hash])
        self.assertEqual(len(control), 33)
        self.assertEqual(control[0] & 1, 1)
        self.assertTrue(verify_p2mr_merkle_path(script=left.script, control_block=control, expected_root=root))
        self.assertFalse(verify_p2mr_merkle_path(script=b"\x53", control_block=control, expected_root=root))

    def test_depth_zero_control_block_refused_by_default(self):
        root = tapleaf_hash(b"\x51")
        with self.assertRaises(P2MrDraftError):
            p2mr_control_block(0xC0, [])
        control = p2mr_control_block(0xC0, [], allow_depth_zero_test_vector=True)
        with self.assertRaises(P2MrDraftError):
            verify_p2mr_merkle_path(script=b"\x51", control_block=control, expected_root=root)
        self.assertTrue(verify_p2mr_merkle_path(
            script=b"\x51", control_block=control, expected_root=root, allow_depth_zero_test_vector=True
        ))


if __name__ == "__main__":
    unittest.main()

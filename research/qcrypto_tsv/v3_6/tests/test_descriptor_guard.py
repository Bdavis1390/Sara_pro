from __future__ import annotations

import hashlib
import unittest

from worldshepherd_qcrypto_kms.descriptor_guard import audit_descriptor


def _b58check(payload: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    n = int.from_bytes(raw, "big")
    chars = []
    while n:
        n, r = divmod(n, 58)
        chars.append(alphabet[r])
    leading = len(raw) - len(raw.lstrip(b"\x00"))
    return "1" * leading + "".join(reversed(chars or ["1"]))


class DescriptorGuardTests(unittest.TestCase):
    def test_extended_private_key_is_hard_rejected(self):
        d = audit_descriptor("wpkh(xprv" + "A" * 80 + "/0/*)")
        self.assertFalse(d.allowed_for_external_signing_boundary)
        self.assertEqual(d.private_extended_key_count, 1)
        self.assertIn("REMOVE_PRIVATE_KEYS_FROM_TRANSFER_DESCRIPTOR", d.required_controls)

    def test_wif_private_key_is_hard_rejected(self):
        wif = _b58check(b"\x80" + (1).to_bytes(32, "big") + b"\x01")
        d = audit_descriptor(f"wpkh({wif})")
        self.assertFalse(d.allowed_for_external_signing_boundary)
        self.assertEqual(d.wif_private_key_count, 1)

    def test_xpub_is_rejected_by_default_and_can_be_explicitly_allowed(self):
        descriptor = "wpkh(xpub" + "B" * 80 + "/0/*)"
        blocked = audit_descriptor(descriptor)
        allowed = audit_descriptor(descriptor, allow_public_extended_keys=True)
        self.assertFalse(blocked.allowed_for_external_signing_boundary)
        self.assertTrue(allowed.allowed_for_external_signing_boundary)
        self.assertEqual(allowed.public_extended_key_count, 1)

    def test_taproot_is_flagged_as_long_public_key_exposure(self):
        d = audit_descriptor("tr(" + "11" * 32 + ")")
        self.assertTrue(d.allowed_for_external_signing_boundary)
        self.assertEqual(d.script_family, "P2TR")
        self.assertIn("DO_NOT_CREATE_NEW_LONG_EXPOSURE_OUTPUTS_IN_HARDENED_POLICY", d.required_controls)

    def test_wpkh_raw_pubkey_is_hidden_until_spend_family(self):
        d = audit_descriptor("wpkh(02" + "11" * 32 + ")")
        self.assertTrue(d.allowed_for_external_signing_boundary)
        self.assertEqual(d.script_family, "P2WPKH_FAMILY")
        self.assertEqual(d.raw_public_key_count, 1)
        self.assertIn("NO_ADDRESS_REUSE", d.required_controls)

    def test_raw_and_unknown_descriptors_fail_closed(self):
        self.assertFalse(audit_descriptor("raw(51)").allowed_for_external_signing_boundary)
        self.assertFalse(audit_descriptor("futurething(foo)").allowed_for_external_signing_boundary)


if __name__ == "__main__":
    unittest.main()

class DescriptorChecksumTests(unittest.TestCase):
    def test_bip380_checksum_vector(self):
        from worldshepherd_qcrypto_kms.descriptor_guard import descriptor_checksum, descriptor_checksum_valid, descriptor_with_checksum
        self.assertEqual(descriptor_checksum("raw(deadbeef)"), "89f8spxm")
        self.assertEqual(descriptor_with_checksum("raw(deadbeef)"), "raw(deadbeef)#89f8spxm")
        self.assertTrue(descriptor_checksum_valid("raw(deadbeef)#89f8spxm"))
        self.assertFalse(descriptor_checksum_valid("raw(deedbeef)#89f8spxm"))

    def test_invalid_checksum_is_hard_rejected(self):
        d = audit_descriptor("wpkh(0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798)#aaaaaaaa")
        self.assertFalse(d.allowed_for_external_signing_boundary)
        self.assertFalse(d.checksum_valid)

    def test_checksum_can_be_required(self):
        from worldshepherd_qcrypto_kms.descriptor_guard import descriptor_with_checksum
        body = "wpkh(0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798)"
        self.assertFalse(audit_descriptor(body, require_checksum=True).allowed_for_external_signing_boundary)
        self.assertTrue(audit_descriptor(descriptor_with_checksum(body), require_checksum=True).allowed_for_external_signing_boundary)

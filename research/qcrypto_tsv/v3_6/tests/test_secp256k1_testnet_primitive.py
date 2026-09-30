from __future__ import annotations

import tempfile
import unittest

from worldshepherd_qcrypto_kms.operation_journal import FileOperationJournal
from worldshepherd_qcrypto_kms.secp256k1_testnet_primitive import (
    AwsKmsSecp256k1TestnetDigestSigner,
    ClassicalSignerError,
)


class Fake:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def describe_key(self, **kw):
        return {"KeyMetadata": {
            "KeySpec": "ECC_SECG_P256K1",
            "KeyUsage": "SIGN_VERIFY",
            "Enabled": True,
            "KeyState": "Enabled",
            "Arn": "arn:aws:kms:us-east-1:111122223333:key/classical",
        }}

    def sign(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise TimeoutError("ambiguous")
        return {
            "KeyId": "arn:aws:kms:us-east-1:111122223333:key/classical",
            "SigningAlgorithm": "ECDSA_SHA_256",
            "Signature": b"DER-SIG",
            "ResponseMetadata": {"RequestId": "req-ecc"},
        }


class ClassicalPrimitiveTests(unittest.TestCase):
    def journal(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return FileOperationJournal(td.name)

    def signer(self, fake, journal=None):
        return AwsKmsSecp256k1TestnetDigestSigner(
            kms_client=fake,
            key_id="alias/ecc",
            operation_journal=journal or self.journal(),
        )

    def test_public_testnet_digest_only(self):
        f = Fake()
        s = self.signer(f)
        r = s.sign_digest(chain="BITCOIN", network="SIGNET", digest32=b"x" * 32)
        self.assertFalse(r.transaction_serialized)
        self.assertFalse(r.transaction_broadcast)
        self.assertFalse(r.mainnet)
        self.assertFalse(r.post_quantum)
        self.assertTrue(r.operation_id.startswith("QCRYPTO-SECP256K1-"))
        self.assertEqual(f.calls[0]["MessageType"], "DIGEST")
        self.assertEqual(f.calls[0]["SigningAlgorithm"], "ECDSA_SHA_256")

    def test_mainnet_rejected_before_sign(self):
        f = Fake()
        s = self.signer(f)
        for chain, network in [("BITCOIN", "MAINNET"), ("ETHEREUM", "MAINNET")]:
            with self.assertRaises(ClassicalSignerError):
                s.sign_digest(chain=chain, network=network, digest32=b"x" * 32)
        self.assertEqual(f.calls, [])

    def test_wrong_digest_length_rejected(self):
        f = Fake()
        s = self.signer(f)
        with self.assertRaises(ClassicalSignerError):
            s.sign_digest(chain="ETHEREUM", network="SEPOLIA", digest32=b"x" * 31)
        self.assertEqual(f.calls, [])

    def test_signed_result_replays_after_restart_without_second_sign(self):
        f = Fake()
        j = self.journal()
        s1 = self.signer(f, j)
        r1 = s1.sign_digest(chain="BITCOIN", network="SIGNET", digest32=b"y" * 32)
        s2 = self.signer(f, j)
        r2 = s2.sign_digest(chain="BITCOIN", network="SIGNET", digest32=b"y" * 32)
        self.assertEqual(r1.der_signature, r2.der_signature)
        self.assertEqual(len(f.calls), 1)

    def test_ambiguous_result_is_durable_and_not_retried_after_restart(self):
        j = self.journal()
        f1 = Fake(fail=True)
        s1 = self.signer(f1, j)
        with self.assertRaises(ClassicalSignerError):
            s1.sign_digest(chain="BITCOIN", network="SIGNET", digest32=b"z" * 32)
        self.assertEqual(len(f1.calls), 1)

        f2 = Fake(fail=False)
        s2 = self.signer(f2, j)
        with self.assertRaises(ClassicalSignerError):
            s2.sign_digest(chain="BITCOIN", network="SIGNET", digest32=b"z" * 32)
        self.assertEqual(len(f2.calls), 0)


if __name__ == "__main__":
    unittest.main()

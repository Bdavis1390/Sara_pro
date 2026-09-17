import unittest

from native_execution_admission import NativeExecutionEvidence, assess_native_execution


class NativeExecutionAdmissionTests(unittest.TestCase):
    def base(self, **overrides):
        values = dict(
            chain="BITCOIN",
            network="SIGNET",
            network_identity_verified=True,
            exact_unsigned_digest_bound_to_approval=True,
            external_signer_attestation_verified=True,
            chain_native_signature_verified=True,
            signed_transaction_digest_verified=True,
        )
        values.update(overrides)
        return NativeExecutionEvidence(**values)

    def test_native_signature_does_not_imply_broadcast(self):
        result = assess_native_execution(self.base())
        self.assertEqual(result.state, "NATIVE_SIGNATURE_EVIDENCE_RECORDED")
        self.assertTrue(result.native_signature_claim)
        self.assertFalse(result.broadcast_claim)
        self.assertFalse(result.mainnet_authority_claim)
        self.assertFalse(result.real_value_movement_claim)
        self.assertTrue(result.qcrypto_authority_remains_false)

    def test_testnet_broadcast_does_not_imply_mainnet_authority(self):
        result = assess_native_execution(
            self.base(
                broadcast_receipt_verified=True,
                canonical_transaction_id_recorded=True,
            )
        )
        self.assertEqual(result.state, "TESTNET_BROADCAST_EVIDENCE_RECORDED")
        self.assertTrue(result.broadcast_claim)
        self.assertFalse(result.mainnet_authority_claim)
        self.assertFalse(result.real_value_movement_claim)

    def test_broadcast_without_signature_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "without verified native signature"):
            assess_native_execution(
                self.base(
                    chain_native_signature_verified=False,
                    broadcast_receipt_verified=True,
                    canonical_transaction_id_recorded=True,
                )
            )

    def test_mainnet_authorization_cannot_be_reused_on_testnet(self):
        with self.assertRaisesRegex(ValueError, "invalid for a test network"):
            assess_native_execution(
                self.base(distinct_mainnet_authorization_recorded=True)
            )

    def test_mainnet_broadcast_requires_distinct_authorization(self):
        evidence = self.base(
            network="MAINNET",
            broadcast_receipt_verified=True,
            canonical_transaction_id_recorded=True,
        )
        result = assess_native_execution(evidence)
        self.assertEqual(result.state, "MAINNET_BROADCAST_WITHOUT_AUTHORITY")
        self.assertTrue(result.broadcast_claim)
        self.assertFalse(result.mainnet_authority_claim)

        authorized = assess_native_execution(
            self.base(
                network="MAINNET",
                broadcast_receipt_verified=True,
                canonical_transaction_id_recorded=True,
                distinct_mainnet_authorization_recorded=True,
            )
        )
        self.assertTrue(authorized.mainnet_authority_claim)
        self.assertFalse(authorized.real_value_movement_claim)

    def test_real_value_requires_full_mainnet_chain(self):
        with self.assertRaisesRegex(ValueError, "real-value evidence"):
            assess_native_execution(
                self.base(
                    network="MAINNET",
                    real_value_execution_receipt_verified=True,
                )
            )
        result = assess_native_execution(
            self.base(
                network="MAINNET",
                broadcast_receipt_verified=True,
                canonical_transaction_id_recorded=True,
                distinct_mainnet_authorization_recorded=True,
                real_value_execution_receipt_verified=True,
            )
        )
        self.assertEqual(result.state, "REAL_VALUE_EXECUTION_EVIDENCE_RECORDED")
        self.assertTrue(result.real_value_movement_claim)

    def test_qcrypto_cannot_self_grant_native_execution_authority(self):
        for field in (
            "qcrypto_execution_authority",
            "qcrypto_private_key_operations_permitted",
            "qcrypto_broadcast_permitted",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "may not self-grant"):
                    assess_native_execution(self.base(**{field: True}))

    def test_ethereum_hoodi_uses_same_evidence_separation(self):
        result = assess_native_execution(
            self.base(chain="ETHEREUM", network="HOODI")
        )
        self.assertTrue(result.native_signature_claim)
        self.assertFalse(result.broadcast_claim)
        self.assertFalse(result.mainnet_authority_claim)


if __name__ == "__main__":
    unittest.main()

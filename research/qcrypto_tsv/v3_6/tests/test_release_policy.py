from __future__ import annotations

import unittest

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.release_policy import (
    BitcoinReleaseIntent,
    PqReleaseAttestation,
    ReleasePolicyError,
    authorize_release,
)

H1 = "11" * 32
H2 = "22" * 32
H3 = "33" * 32


class ReleasePolicyTests(unittest.TestCase):
    def intent(self):
        return BitcoinReleaseIntent(
            network="SIGNET",
            unsigned_tx_sha256=H1,
            input_set_sha256=H2,
            output_set_sha256=H3,
            fee_sat=1000,
            policy_epoch="2026-09-18",
            signing_policy_sha256="44" * 32,
            authorization_nonce="nonce-0123456789abcdef",
            expires_at="2099-01-01T00:00:00Z",
        )

    def attestation(self, digest):
        return PqReleaseAttestation(
            intent_sha256=digest,
            pq_algorithm="ML_DSA_SHAKE_256",
            pq_key_fingerprint_sha256="aa" * 32,
            pq_signature_b64url="c2ln",
            provider_operation_id="QCRYPTO-AWS-KMS-" + "ab" * 32,
        )

    def test_hybrid_state_requires_exact_pq_binding(self):
        intent = self.intent()
        with self.assertRaises(ReleasePolicyError):
            authorize_release(intent=intent, policy_state=CryptoPolicyState.HYBRID_REQUIRED, pq_attestation=None)
        with self.assertRaises(ReleasePolicyError):
            authorize_release(intent=intent, policy_state=CryptoPolicyState.HYBRID_REQUIRED, pq_attestation=self.attestation("ff" * 32))
        with self.assertRaises(ReleasePolicyError):
            authorize_release(
                intent=intent,
                policy_state=CryptoPolicyState.HYBRID_REQUIRED,
                pq_attestation=self.attestation(intent.intent_sha256),
            )
        out = authorize_release(
            intent=intent,
            policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            pq_attestation=self.attestation(intent.intent_sha256),
            pq_signature_verifier=lambda message, context, signature: signature == b"sig",
        )
        self.assertTrue(out["authorized_for_local_signing_workflow"])
        self.assertTrue(out["pq_signature_verified"])
        self.assertFalse(out["bitcoin_consensus_pq_security_established"])
        self.assertFalse(out["transaction_broadcast_authorized"])

    def test_classical_rejected_state_blocks_release(self):
        intent = self.intent()
        with self.assertRaises(ReleasePolicyError):
            authorize_release(
                intent=intent,
                policy_state=CryptoPolicyState.CLASSICAL_REJECTED,
                pq_attestation=self.attestation(intent.intent_sha256),
            )

    def test_mainnet_intent_is_blocked(self):
        bad = BitcoinReleaseIntent(
            network="MAINNET",
            unsigned_tx_sha256=H1,
            input_set_sha256=H2,
            output_set_sha256=H3,
            fee_sat=1,
            policy_epoch="x",
            signing_policy_sha256="44" * 32,
            authorization_nonce="nonce-0123456789abcdef",
            expires_at="2099-01-01T00:00:00Z",
        )
        with self.assertRaises(ReleasePolicyError):
            _ = bad.intent_sha256

    def test_unknown_network_aliases_empty_epoch_and_bad_attestation_fail_closed(self):
        for network in ("BITCOIN_MAINNET", "BTC_MAINNET", "MYSTERY"):
            bad = BitcoinReleaseIntent(network=network, unsigned_tx_sha256=H1, input_set_sha256=H2, output_set_sha256=H3, fee_sat=1, policy_epoch="epoch", signing_policy_sha256="44" * 32, authorization_nonce="nonce-0123456789abcdef", expires_at="2099-01-01T00:00:00Z")
            with self.assertRaises(ReleasePolicyError):
                _ = bad.intent_sha256
        bad_epoch = BitcoinReleaseIntent(network="SIGNET", unsigned_tx_sha256=H1, input_set_sha256=H2, output_set_sha256=H3, fee_sat=1, policy_epoch="   ", signing_policy_sha256="44" * 32, authorization_nonce="nonce-0123456789abcdef", expires_at="2099-01-01T00:00:00Z")
        with self.assertRaises(ReleasePolicyError):
            _ = bad_epoch.intent_sha256
        intent = self.intent()
        bad = self.attestation(intent.intent_sha256)
        bad = PqReleaseAttestation(
            intent_sha256=bad.intent_sha256, pq_algorithm=bad.pq_algorithm,
            pq_key_fingerprint_sha256="nothex", pq_signature_b64url=bad.pq_signature_b64url,
            provider_operation_id=bad.provider_operation_id,
        )
        with self.assertRaises(ReleasePolicyError):
            authorize_release(intent=intent, policy_state=CryptoPolicyState.HYBRID_REQUIRED, pq_attestation=bad)

    def test_pq_required_cannot_be_satisfied_by_detached_attestation_only(self):
        intent = self.intent()
        with self.assertRaises(ReleasePolicyError):
            authorize_release(
                intent=intent, policy_state=CryptoPolicyState.PQ_REQUIRED,
                pq_attestation=self.attestation(intent.intent_sha256),
            )


if __name__ == "__main__":
    unittest.main()

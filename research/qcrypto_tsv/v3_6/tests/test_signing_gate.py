from __future__ import annotations

import base64
import hashlib
import unittest
from types import SimpleNamespace

from worldshepherd_qcrypto_kms.aws_kms_provider import ProviderState, provider_operation_id
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, encode_compact_size
from worldshepherd_qcrypto_kms.release_policy import (
    RELEASE_ATTESTATION_CONTEXT,
    PqReleaseAttestation,
    ReleasePolicyError,
    build_pq_release_attestation_from_provider_result,
)
from worldshepherd_qcrypto_kms.signing_gate import (
    SigningGateError,
    authorize_prepared_signing,
    prepare_psbt_signing,
)

MAGIC = b"psbt\xff"
P2WPKH = bytes.fromhex("0014" + "11" * 20)
P2TR = bytes.fromhex("5120" + "22" * 32)
INPUT_P2WPKH = bytes.fromhex("0014" + "33" * 20)


def kv(key_type: int, value: bytes, key_data: bytes = b"") -> bytes:
    key = encode_compact_size(key_type) + key_data
    return encode_compact_size(len(key)) + key + encode_compact_size(len(value)) + value


def mp(*entries: bytes) -> bytes:
    return b"".join(entries) + b"\x00"


def witness_utxo(value_sat: int, script: bytes) -> bytes:
    return value_sat.to_bytes(8, "little") + encode_compact_size(len(script)) + script


def make_psbt(script: bytes = P2WPKH, *, input_value: int = 100_000, output_value: int = 90_000) -> bytes:
    tx = BitcoinTransaction(
        version=2,
        inputs=(TxInput(prev_txid="77" * 32, vout=0, script_sig=b"", sequence=0xFFFFFFFE),),
        outputs=(TxOutput(value_sat=output_value, script_pubkey=script),),
        locktime=0,
        segwit=False,
    )
    return MAGIC + mp(kv(0x00, tx.serialize())) + mp(kv(0x01, witness_utxo(input_value, INPUT_P2WPKH))) + mp()


def auth_window():
    return {"authorization_nonce": "nonce-0123456789abcdef", "expires_at": "2099-01-01T00:00:00Z"}


class SigningGateTests(unittest.TestCase):
    def test_prepared_gate_binds_exact_psbt_transaction_and_fee(self):
        raw = make_psbt()
        p = prepare_psbt_signing(
            raw,
            network="SIGNET",
            policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            policy_epoch="2026-09-18T15:00-04:00",
            max_fee_sat=20_000,
            **auth_window(),
        )
        self.assertEqual(p.psbt_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(p.intent.fee_sat, 10_000)
        self.assertEqual(len(p.intent.input_set_sha256), 64)
        self.assertEqual(len(p.intent.output_set_sha256), 64)
        auth = authorize_prepared_signing(p)
        self.assertTrue(auth["authorized_for_local_signing_workflow"])
        self.assertFalse(auth["transaction_broadcast_authorized"])

    def test_fee_cap_is_mandatory_and_enforced_before_authorization(self):
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(
                make_psbt(input_value=200_000, output_value=90_000),
                network="SIGNET",
                policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                policy_epoch="epoch",
                max_fee_sat=50_000,
                **auth_window(),
            )

    def test_descriptor_private_key_blocks_prepared_gate(self):
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(
                make_psbt(),
                network="SIGNET",
                policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                policy_epoch="epoch",
                max_fee_sat=20_000,
                **auth_window(),
                descriptors=("wpkh(xprv" + "A" * 80 + "/0/*)",),
            )

    def test_hybrid_gate_requires_verified_pq_attestation(self):
        p = prepare_psbt_signing(
            make_psbt(),
            network="SIGNET",
            policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            policy_epoch="epoch",
            max_fee_sat=20_000,
            **auth_window(),
            pq_recovery_output_indexes={0},
        )
        att = PqReleaseAttestation(
            intent_sha256=p.intent.intent_sha256,
            pq_algorithm="ML_DSA_SHAKE_256",
            pq_key_fingerprint_sha256="aa" * 32,
            pq_signature_b64url=base64.urlsafe_b64encode(b"sig").rstrip(b"=").decode(),
            provider_operation_id="QCRYPTO-AWS-KMS-" + "ab" * 32,
        )
        with self.assertRaises(SigningGateError):
            authorize_prepared_signing(p, pq_attestation=att)
        with self.assertRaises(SigningGateError):
            authorize_prepared_signing(p, pq_attestation=att, pq_signature_verifier=lambda m, c, s: False)
        out = authorize_prepared_signing(p, pq_attestation=att, pq_signature_verifier=lambda m, c, s: s == b"sig")
        self.assertTrue(out["authorization"]["pq_signature_verified"])

    def test_hybrid_gate_blocks_long_exposure_p2tr_before_attestation(self):
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(
                make_psbt(P2TR),
                network="SIGNET",
                policy_state=CryptoPolicyState.HYBRID_REQUIRED,
                policy_epoch="epoch",
                max_fee_sat=20_000,
                **auth_window(),
                pq_recovery_output_indexes={0},
            )

    def test_provider_result_attestation_builder_checks_exact_operation_binding(self):
        p = prepare_psbt_signing(
            make_psbt(), network="SIGNET", policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            policy_epoch="epoch", max_fee_sat=20_000, **auth_window(), pq_recovery_output_indexes={0},
        )
        key_arn = "arn:aws:kms:us-east-1:123456789012:key/00000000-0000-0000-0000-000000000000"
        descriptor = SimpleNamespace(key_arn=key_arn, public_key_der_sha256="aa" * 32)
        message = p.intent.canonical_bytes()
        op = provider_operation_id(key_arn=key_arn, message=message, context=RELEASE_ATTESTATION_CONTEXT)
        result = SimpleNamespace(
            operation_id=op,
            state=ProviderState.SIGNED,
            key_arn=key_arn,
            algorithm="ML_DSA_SHAKE_256",
            message_sha256=hashlib.sha256(message).hexdigest(),
            context_sha256=hashlib.sha256(RELEASE_ATTESTATION_CONTEXT).hexdigest(),
            signature_b64url="c2ln",
        )
        a = build_pq_release_attestation_from_provider_result(intent=p.intent, descriptor=descriptor, result=result)
        self.assertEqual(a.provider_operation_id, op)
        bad = SimpleNamespace(**{**result.__dict__, "message_sha256": "00" * 32})
        with self.assertRaises(ReleasePolicyError):
            build_pq_release_attestation_from_provider_result(intent=p.intent, descriptor=descriptor, result=bad)


if __name__ == "__main__":
    unittest.main()

class SigningGateDescriptorChecksumTests(unittest.TestCase):
    def test_signing_gate_requires_bip380_checksum_for_supplied_descriptor(self):
        from worldshepherd_qcrypto_kms.descriptor_guard import descriptor_with_checksum
        body = "wpkh(0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798)"
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(make_psbt(), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                                 policy_epoch="epoch", max_fee_sat=20_000, **auth_window(), descriptors=(body,))
        p = prepare_psbt_signing(make_psbt(), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                                 policy_epoch="epoch", max_fee_sat=20_000, **auth_window(),
                                 descriptors=(descriptor_with_checksum(body),))
        self.assertTrue(p.descriptor_audits[0].checksum_valid)

from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_qcrypto_kms.address_codec import AddressCodecError, address_to_scriptpubkey, scriptpubkey_to_address
from worldshepherd_qcrypto_kms.approval_quorum import ApprovalStatement, sign_approval
from worldshepherd_qcrypto_kms.authorization_ledger import AuthorizationLedgerError, verify_authorization_ledger
from worldshepherd_qcrypto_kms.bitcoin_core_interop import BitcoinCoreInteropError, core_capabilities
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, encode_compact_size
from worldshepherd_qcrypto_kms.output_intent import ExpectedPayment, OutputIntentPolicy
from worldshepherd_qcrypto_kms.psbt_guard import PsbtGuardError, audit_psbt, parse_psbt
from worldshepherd_qcrypto_kms.release_policy import BitcoinReleaseIntent, ReleasePolicyError, authorize_release
from worldshepherd_qcrypto_kms.signature_policy import (
    SECP256K1_N,
    SignaturePolicyError,
    parse_schnorr_signature,
    parse_strict_der_ecdsa_signature,
)
from worldshepherd_qcrypto_kms.signing_gate import SigningGateError, authorize_prepared_signing, prepare_psbt_signing

MAGIC = b"psbt\xff"
INPUT = bytes.fromhex("0014" + "33" * 20)
PAYEE = bytes.fromhex("0014" + "11" * 20)
CHANGE = bytes.fromhex("0014" + "22" * 20)
P2TR = bytes.fromhex("5120" + "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")
G = bytes.fromhex("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")


def kv(key_type: int, value: bytes, key_data: bytes = b"") -> bytes:
    key = encode_compact_size(key_type) + key_data
    return encode_compact_size(len(key)) + key + encode_compact_size(len(value)) + value


def mp(*entries: bytes) -> bytes:
    return b"".join(entries) + b"\x00"


def witness_utxo(value_sat: int, script: bytes) -> bytes:
    return value_sat.to_bytes(8, "little") + encode_compact_size(len(script)) + script


def make_psbt(
    *,
    input_value: int = 100_000,
    input_script: bytes = INPUT,
    outputs: tuple[tuple[int, bytes], ...] = ((99_000, PAYEE),),
    sequence: int = 0xFFFFFFFE,
    input_extra: tuple[bytes, ...] = (),
    global_extra: tuple[bytes, ...] = (),
) -> bytes:
    tx = BitcoinTransaction(
        version=2,
        inputs=(TxInput(prev_txid="77" * 32, vout=0, script_sig=b"", sequence=sequence),),
        outputs=tuple(TxOutput(value_sat=v, script_pubkey=s) for v, s in outputs),
        locktime=0,
        segwit=False,
    )
    return MAGIC + mp(kv(0x00, tx.serialize()), *global_extra) + mp(kv(0x01, witness_utxo(input_value, input_script)), *input_extra) + mp(*(() for _ in ())) if False else MAGIC + mp(kv(0x00, tx.serialize()), *global_extra) + mp(kv(0x01, witness_utxo(input_value, input_script)), *input_extra) + b"".join(mp() for _ in outputs)


def prepare(raw: bytes, **kwargs):
    base = dict(
        network="SIGNET",
        policy_state=CryptoPolicyState.ECDSA_ALLOWED,
        policy_epoch="2026-09-18-v2",
        max_fee_sat=20_000,
        authorization_nonce="nonce-0123456789abcdef",
        expires_at="2099-01-01T00:00:00Z",
    )
    base.update(kwargs)
    return prepare_psbt_signing(raw, **base)


class AddressBindingTests(unittest.TestCase):
    def test_network_bound_address_roundtrip(self):
        for script in (PAYEE, P2TR):
            addr = scriptpubkey_to_address(script, network="SIGNET")
            self.assertEqual(address_to_scriptpubkey(addr, network="SIGNET"), script)
            with self.assertRaises(AddressCodecError):
                address_to_scriptpubkey(addr, network="REGTEST")


class SignatureFirewallTests(unittest.TestCase):
    def test_strict_der_low_s_and_high_s_rejection(self):
        good = bytes.fromhex("300602010102010101")
        parsed = parse_strict_der_ecdsa_signature(good)
        self.assertEqual(parsed.sighash_type, 1)
        high_s = SECP256K1_N - 1
        sb = high_s.to_bytes(32, "big")
        if sb[0] & 0x80:
            sb = b"\x00" + sb
        der = b"\x30" + bytes([2 + 1 + 2 + len(sb)]) + b"\x02\x01\x01\x02" + bytes([len(sb)]) + sb + b"\x01"
        with self.assertRaises(SignaturePolicyError):
            parse_strict_der_ecdsa_signature(der)

    def test_schnorr_range_and_explicit_default_sighash_rejection(self):
        self.assertEqual(parse_schnorr_signature(b"\x00" * 64).sighash_type, 0)
        with self.assertRaises(SignaturePolicyError):
            parse_schnorr_signature(b"\x00" * 64 + b"\x00")
        with self.assertRaises(SignaturePolicyError):
            parse_schnorr_signature((2**256 - 1).to_bytes(32, "big") + b"\x00" * 32)

    def test_psbt_sighash_anyonecanpay_is_blocked(self):
        raw = make_psbt(input_extra=(kv(0x03, (0x81).to_bytes(4, "little")),))
        with self.assertRaises(PsbtGuardError):
            audit_psbt(raw, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)

    def test_finalized_input_cannot_retain_partial_signatures(self):
        partial = kv(0x02, bytes.fromhex("300602010102010101"), G)
        final = kv(0x08, b"\x00")  # empty serialized witness stack
        raw = make_psbt(input_extra=(partial, final))
        with self.assertRaises(PsbtGuardError):
            parse_psbt(raw)


class PsbtBoundaryTests(unittest.TestCase):
    def test_unknown_and_unapproved_proprietary_fields_fail_closed(self):
        raw_unknown = make_psbt(global_extra=(kv(0x90, b"x"),))
        report = audit_psbt(raw_unknown, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)
        self.assertFalse(report.allowed)
        self.assertEqual(report.metadata_exposure["unknown_field_count"], 1)

        prop_key_data = encode_compact_size(2) + b"ws" + encode_compact_size(1)
        raw_prop = make_psbt(global_extra=(kv(0xFC, b"x", prop_key_data),))
        self.assertFalse(audit_psbt(raw_prop, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED).allowed)
        ok = audit_psbt(
            raw_prop,
            network="SIGNET",
            policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            allowed_proprietary_prefixes=(b"ws",),
        )
        self.assertTrue(ok.allowed)

    def test_duplicate_prevout_in_same_psbt_is_rejected(self):
        tx = BitcoinTransaction(
            version=2,
            inputs=(
                TxInput(prev_txid="77" * 32, vout=0, script_sig=b"", sequence=0xFFFFFFFE),
                TxInput(prev_txid="77" * 32, vout=0, script_sig=b"", sequence=0xFFFFFFFE),
            ),
            outputs=(TxOutput(value_sat=199_000, script_pubkey=PAYEE),),
            locktime=0,
            segwit=False,
        )
        raw = MAGIC + mp(kv(0x00, tx.serialize())) + mp(kv(0x01, witness_utxo(100_000, INPUT))) + mp(kv(0x01, witness_utxo(100_000, INPUT))) + mp()
        with self.assertRaises(PsbtGuardError):
            audit_psbt(raw, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)

    def test_address_reuse_is_rejected_by_high_assurance_gate(self):
        with self.assertRaises(SigningGateError):
            prepare(make_psbt(outputs=((99_000, INPUT),)))

    def test_rbf_signaling_is_rejected_by_high_assurance_gate(self):
        with self.assertRaises(SigningGateError):
            prepare(make_psbt(sequence=0xFFFFFFFD))

    def test_dust_output_is_rejected(self):
        raw = make_psbt(outputs=((100, PAYEE), (99_800, CHANGE)))
        with self.assertRaises(SigningGateError):
            prepare(raw)

    def test_fee_ratio_and_feerate_upper_bound_are_enforced(self):
        ratio = make_psbt(outputs=((80_000, PAYEE),))
        with self.assertRaises(SigningGateError):
            prepare(ratio, max_fee_sat=30_000, max_fee_bps_of_input=1000, max_fee_rate_upper_bound_sat_vb=1000)
        rate = make_psbt(outputs=((90_000, PAYEE),))
        with self.assertRaises(SigningGateError):
            prepare(rate, max_fee_sat=20_000, max_fee_bps_of_input=2000, max_fee_rate_upper_bound_sat_vb=100)


class OutputIntentTests(unittest.TestCase):
    def test_exact_recipient_and_allowlisted_change_are_bound(self):
        payee_addr = scriptpubkey_to_address(PAYEE, network="SIGNET")
        change_addr = scriptpubkey_to_address(CHANGE, network="SIGNET")
        raw = make_psbt(outputs=((50_000, PAYEE), (49_000, CHANGE)))
        policy = OutputIntentPolicy(
            expected_payments=(ExpectedPayment(amount_sat=50_000, address=payee_addr, label="recipient"),),
            allowed_change_addresses=(change_addr,),
            max_change_outputs=1,
        )
        p = prepare(raw, output_intent_policy=policy, require_output_intent=True)
        self.assertTrue(p.output_intent_report and p.output_intent_report.satisfied)
        self.assertEqual(p.output_intent_report.matched_payment_indexes, (0,))
        self.assertEqual(p.output_intent_report.change_output_indexes, (1,))

    def test_output_injection_is_rejected(self):
        payee_addr = scriptpubkey_to_address(PAYEE, network="SIGNET")
        raw = make_psbt(outputs=((50_000, PAYEE), (49_000, CHANGE)))
        policy = OutputIntentPolicy(expected_payments=(ExpectedPayment(amount_sat=50_000, address=payee_addr),), max_change_outputs=0)
        with self.assertRaises(SigningGateError):
            prepare(raw, output_intent_policy=policy, require_output_intent=True)


class IntentGovernanceTests(unittest.TestCase):
    def test_policy_commitment_changes_intent_hash(self):
        raw = make_psbt()
        a = prepare(raw, reject_dust=True)
        b = prepare(raw, reject_dust=False)
        self.assertNotEqual(a.signing_policy_sha256, b.signing_policy_sha256)
        self.assertNotEqual(a.intent.intent_sha256, b.intent.intent_sha256)

    def test_expired_release_intent_is_rejected(self):
        intent = BitcoinReleaseIntent(
            network="SIGNET",
            unsigned_tx_sha256="11" * 32,
            input_set_sha256="22" * 32,
            output_set_sha256="33" * 32,
            fee_sat=1,
            policy_epoch="epoch",
            signing_policy_sha256="44" * 32,
            authorization_nonce="nonce-0123456789abcdef",
            expires_at="2026-01-01T00:00:00Z",
        )
        with self.assertRaises(ReleasePolicyError):
            authorize_release(
                intent=intent,
                policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                pq_attestation=None,
                now=dt.datetime(2026, 9, 18, tzinfo=dt.timezone.utc),
            )

    def test_two_operator_quorum_and_hash_chained_receipt(self):
        raw = make_psbt()
        prepared = prepare(raw)
        k1 = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        k2 = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
        now = dt.datetime(2026, 9, 18, 19, 0, tzinfo=dt.timezone.utc)
        statements = [
            ApprovalStatement(prepared.intent.intent_sha256, "creator", "CREATOR", "2026-09-18T18:00:00Z", "2026-09-19T18:00:00Z", "approval-nonce-creator"),
            ApprovalStatement(prepared.intent.intent_sha256, "operator", "OPERATOR", "2026-09-18T18:00:00Z", "2026-09-19T18:00:00Z", "approval-nonce-operator"),
        ]
        approvals = (sign_approval(statements[0], k1), sign_approval(statements[1], k2))
        trusted = {
            "creator": k1.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
            "operator": k2.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
        }
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "authorization.jsonl"
            out = authorize_prepared_signing(
                prepared,
                approvals=approvals,
                trusted_approvers=trusted,
                required_approval_count=2,
                required_approval_roles=("CREATOR", "OPERATOR"),
                authorization_ledger_path=str(ledger),
                now=now,
            )
            self.assertTrue(out["operator_quorum"]["satisfied"])
            self.assertEqual(verify_authorization_ledger(ledger)["records"], 1)
            data = ledger.read_bytes()
            ledger.write_bytes(data.replace(b'"sequence":1', b'"sequence":9', 1))
            with self.assertRaises(AuthorizationLedgerError):
                verify_authorization_ledger(ledger)


class CoreCapabilityTests(unittest.TestCase):
    def test_core_version_capability_negotiation_tracks_psbtv2_transition(self):
        c31 = core_capabilities(310100)
        c32 = core_capabilities(320000)
        self.assertTrue(c31["musig2_psbt_bip373"])
        self.assertFalse(c31["psbt_v2_bip370"])
        self.assertTrue(c32["psbt_v2_bip370"])
        with self.assertRaises(BitcoinCoreInteropError):
            core_capabilities(-1)


if __name__ == "__main__":
    unittest.main()

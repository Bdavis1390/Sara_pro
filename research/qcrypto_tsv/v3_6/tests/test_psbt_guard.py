from __future__ import annotations

import hashlib
import unittest

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, encode_compact_size
from worldshepherd_qcrypto_kms.psbt_guard import PsbtGuardError, audit_psbt, parse_psbt

MAGIC = b"psbt\xff"
P2WPKH = bytes.fromhex("0014" + "11" * 20)
P2TR = bytes.fromhex("5120" + "22" * 32)


def kv(key_type: int, value: bytes, key_data: bytes = b"") -> bytes:
    key = encode_compact_size(key_type) + key_data
    return encode_compact_size(len(key)) + key + encode_compact_size(len(value)) + value


def mp(*entries: bytes) -> bytes:
    return b"".join(entries) + b"\x00"


def witness_utxo(value_sat: int, script: bytes) -> bytes:
    return value_sat.to_bytes(8, "little") + encode_compact_size(len(script)) + script


def unsigned_transaction(script: bytes, *, input_value: int = 100_000, output_value: int = 90_000) -> BitcoinTransaction:
    return BitcoinTransaction(
        version=2,
        inputs=(TxInput(prev_txid="77" * 32, vout=0, script_sig=b"", sequence=0xFFFFFFFD),),
        outputs=(TxOutput(value_sat=output_value, script_pubkey=script),),
        locktime=0,
        segwit=False,
    )


def psbt_v0(script: bytes = P2WPKH, *, xpub: bool = False, duplicate_unsigned: bool = False, input_value: int = 100_000, output_value: int = 90_000) -> bytes:
    tx = unsigned_transaction(script, input_value=input_value, output_value=output_value)
    globals_entries = [kv(0x00, tx.serialize())]
    if duplicate_unsigned:
        globals_entries.append(kv(0x00, tx.serialize()))
    if xpub:
        raw_xpub = bytearray(78)
        raw_xpub[0:4] = bytes.fromhex("0488b21e")
        raw_xpub[4] = 0
        raw_xpub[13:45] = b"\x22" * 32
        raw_xpub[45] = 2
        raw_xpub[46:78] = b"\x33" * 32
        globals_entries.append(kv(0x01, b"\x00\x00\x00\x00", bytes(raw_xpub)))
    return MAGIC + mp(*globals_entries) + mp(kv(0x01, witness_utxo(input_value, script))) + mp()


def psbt_v2(script: bytes = P2WPKH, *, modifiable: int | None = None, partial_sig: bool = False, input_value: int = 100_000, output_value: int = 90_000) -> bytes:
    globals_entries = [
        kv(0xFB, (2).to_bytes(4, "little")),
        kv(0x02, (2).to_bytes(4, "little", signed=True)),
        kv(0x04, encode_compact_size(1)),
        kv(0x05, encode_compact_size(1)),
    ]
    if modifiable is not None:
        globals_entries.append(kv(0x06, bytes([modifiable])))
    input_entries = [
        kv(0x0E, bytes.fromhex("77" * 32)[::-1]),
        kv(0x0F, (0).to_bytes(4, "little")),
        kv(0x10, (0xFFFFFFFD).to_bytes(4, "little")),
        kv(0x01, witness_utxo(input_value, script)),
    ]
    if partial_sig:
        # Structurally valid strict-DER low-S signature with SIGHASH_ALL and generator pubkey.
        g = bytes.fromhex("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")
        input_entries.append(kv(0x02, bytes.fromhex("300602010102010101"), g))
    output_entries = [
        kv(0x03, output_value.to_bytes(8, "little", signed=True)),
        kv(0x04, script),
    ]
    return MAGIC + mp(*globals_entries) + mp(*input_entries) + mp(*output_entries)


class PsbtGuardTests(unittest.TestCase):
    def test_valid_v0_is_parsed_and_fee_is_measured(self):
        parsed = parse_psbt(psbt_v0())
        self.assertEqual(parsed.version, 0)
        report = audit_psbt(psbt_v0(), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED, max_fee_sat=20_000)
        self.assertTrue(report.allowed)
        self.assertEqual(report.fee_sat, 10_000)

    def test_valid_v2_is_reconstructed_and_audited(self):
        parsed = parse_psbt(psbt_v2())
        self.assertEqual(parsed.version, 2)
        self.assertEqual(parsed.transaction.outputs[0].script_pubkey, P2WPKH)
        report = audit_psbt(psbt_v2(), network="TESTNET4", policy_state=CryptoPolicyState.ECDSA_ALLOWED, max_fee_sat=20_000)
        self.assertTrue(report.allowed)

    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(PsbtGuardError):
            parse_psbt(psbt_v0(duplicate_unsigned=True))

    def test_global_xpub_is_rejected_by_default_signing_boundary(self):
        report = audit_psbt(psbt_v0(xpub=True), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)
        self.assertFalse(report.allowed)
        self.assertEqual(report.metadata_exposure["global_xpub_count"], 1)

    def test_global_xpub_can_be_explicitly_permitted_but_is_reported(self):
        report = audit_psbt(
            psbt_v0(xpub=True), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            reject_global_xpub=False,
        )
        self.assertTrue(report.allowed)
        self.assertTrue(any("extended public key" in f for f in report.findings))

    def test_p2tr_is_rejected_under_hybrid_policy(self):
        report = audit_psbt(
            psbt_v0(P2TR), network="SIGNET", policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            pq_recovery_output_indexes={0},
        )
        self.assertFalse(report.allowed)

    def test_mainnet_psbt_is_rejected_even_when_structurally_valid(self):
        report = audit_psbt(psbt_v0(), network="MAINNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)
        self.assertFalse(report.allowed)

    def test_fee_cap_is_enforced(self):
        report = audit_psbt(
            psbt_v0(input_value=200_000, output_value=90_000),
            network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED, max_fee_sat=50_000,
        )
        self.assertFalse(report.allowed)
        self.assertEqual(report.fee_sat, 110_000)

    def test_outputs_cannot_exceed_input_value(self):
        with self.assertRaises(PsbtGuardError):
            audit_psbt(
                psbt_v0(input_value=50_000, output_value=60_000),
                network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            )

    def test_v2_signed_but_still_mutable_is_rejected(self):
        report = audit_psbt(
            psbt_v2(modifiable=0x03, partial_sig=True),
            network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED,
        )
        self.assertFalse(report.allowed)
        self.assertTrue(report.metadata_exposure["mutable_after_signature"])

    def test_missing_utxo_provenance_is_rejected(self):
        tx = unsigned_transaction(P2WPKH)
        raw = MAGIC + mp(kv(0x00, tx.serialize())) + mp() + mp()
        with self.assertRaises(PsbtGuardError):
            audit_psbt(raw, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)

    def test_psbtv0_rejects_v2_only_global_fields(self):
        tx = unsigned_transaction(P2WPKH)
        raw = MAGIC + mp(kv(0x00, tx.serialize()), kv(0x04, encode_compact_size(1))) + mp(kv(0x01, witness_utxo(100_000, P2WPKH))) + mp()
        with self.assertRaises(PsbtGuardError):
            parse_psbt(raw)


    def test_official_bip370_required_fields_vector_parses(self):
        # BIP-370 valid vector: 1 input, 2 outputs, required fields only.
        raw = bytes.fromhex(
            "70736274ff01020402000000010401010105010201fb040200000000"
            "010e200b0ad921419c1c8719735d72dc739f9ea9e0638d1fe4c1eef0f9944084815fc8"
            "010f040000000000"
            "0103080008af2f000000000104160014c430f64c4756da310dbd1a085572ef299926272c00"
            "0103088bbdeb0b0000000001041600144dd193ac964a56ac1b9e1cca8454fe2f474f851300"
        )
        parsed = parse_psbt(raw)
        self.assertEqual(parsed.version, 2)
        self.assertEqual(len(parsed.input_maps), 1)
        self.assertEqual(len(parsed.output_maps), 2)

    def test_psbtv2_required_height_locktime_is_reconstructed(self):
        globals_entries = [
            kv(0xFB, (2).to_bytes(4, "little")), kv(0x02, (2).to_bytes(4, "little", signed=True)),
            kv(0x04, encode_compact_size(1)), kv(0x05, encode_compact_size(1)),
            kv(0x03, (999).to_bytes(4, "little")),
        ]
        input_entries = [
            kv(0x0E, bytes.fromhex("77" * 32)[::-1]), kv(0x0F, (0).to_bytes(4, "little")),
            kv(0x12, (123456).to_bytes(4, "little")), kv(0x01, witness_utxo(100_000, P2WPKH)),
        ]
        out = [kv(0x03, (90_000).to_bytes(8, "little", signed=True)), kv(0x04, P2WPKH)]
        raw = MAGIC + mp(*globals_entries) + mp(*input_entries) + mp(*out)
        parsed = parse_psbt(raw)
        self.assertEqual(parsed.transaction.locktime, 123456)

    def test_psbtv2_incompatible_time_and_height_locktime_requirements_fail(self):
        globals_entries = [
            kv(0xFB, (2).to_bytes(4, "little")), kv(0x02, (2).to_bytes(4, "little", signed=True)),
            kv(0x04, encode_compact_size(2)), kv(0x05, encode_compact_size(1)),
        ]
        inp1 = [kv(0x0E, bytes.fromhex("77" * 32)[::-1]), kv(0x0F, (0).to_bytes(4, "little")), kv(0x11, (500_000_001).to_bytes(4, "little"))]
        inp2 = [kv(0x0E, bytes.fromhex("88" * 32)[::-1]), kv(0x0F, (0).to_bytes(4, "little")), kv(0x12, (100).to_bytes(4, "little"))]
        out = [kv(0x03, (1).to_bytes(8, "little", signed=True)), kv(0x04, P2WPKH)]
        raw = MAGIC + mp(*globals_entries) + mp(*inp1) + mp(*inp2) + mp(*out)
        with self.assertRaises(PsbtGuardError):
            parse_psbt(raw)

    def test_p2sh_redeemscript_commitment_is_verified(self):
        redeem = P2WPKH
        p2sh = b"\xa9\x14" + hashlib.new("ripemd160", hashlib.sha256(redeem).digest()).digest() + b"\x87"
        tx = unsigned_transaction(p2sh)
        good = MAGIC + mp(kv(0x00, tx.serialize())) + mp(
            kv(0x01, witness_utxo(100_000, p2sh)), kv(0x04, redeem)
        ) + mp()
        report = audit_psbt(good, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED, max_fee_sat=20_000)
        self.assertTrue(report.allowed)
        bad_redeem = bytes.fromhex("0014" + "99" * 20)
        bad = MAGIC + mp(kv(0x00, tx.serialize())) + mp(
            kv(0x01, witness_utxo(100_000, p2sh)), kv(0x04, bad_redeem)
        ) + mp()
        with self.assertRaises(PsbtGuardError):
            audit_psbt(bad, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)

    def test_p2wsh_witnessscript_commitment_is_verified(self):
        witness_script = b"\x51"  # OP_TRUE, test-only script material.
        p2wsh = b"\x00\x20" + hashlib.sha256(witness_script).digest()
        tx = unsigned_transaction(p2wsh)
        good = MAGIC + mp(kv(0x00, tx.serialize())) + mp(
            kv(0x01, witness_utxo(100_000, p2wsh)), kv(0x05, witness_script)
        ) + mp()
        report = audit_psbt(good, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED, max_fee_sat=20_000)
        self.assertTrue(report.allowed)
        bad = MAGIC + mp(kv(0x00, tx.serialize())) + mp(
            kv(0x01, witness_utxo(100_000, p2wsh)), kv(0x05, b"\x52")
        ) + mp()
        with self.assertRaises(PsbtGuardError):
            audit_psbt(bad, network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED)


if __name__ == "__main__":
    unittest.main()

class PsbtSemanticFieldValidationTests(unittest.TestCase):
    G = bytes.fromhex("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")

    def _v0_with_extra_input(self, *extra: bytes) -> bytes:
        tx = unsigned_transaction(P2WPKH)
        return MAGIC + mp(kv(0x00, tx.serialize())) + mp(kv(0x01, witness_utxo(100_000, P2WPKH)), *extra) + mp()

    def test_hash_preimage_is_cryptographically_checked(self):
        preimage = b"worldshepherd"
        good = self._v0_with_extra_input(kv(0x0b, preimage, hashlib.sha256(preimage).digest()))
        self.assertEqual(parse_psbt(good).version, 0)
        bad = self._v0_with_extra_input(kv(0x0b, preimage, b"\x00" * 32))
        with self.assertRaises(PsbtGuardError):
            parse_psbt(bad)

    def test_taproot_signature_length_is_checked(self):
        bad = self._v0_with_extra_input(kv(0x13, b"\x00" * 63))
        with self.assertRaises(PsbtGuardError):
            parse_psbt(bad)

    def test_taproot_leaf_control_block_length_is_checked(self):
        # 32-byte key data is too short; control blocks are 33+32m.
        bad = self._v0_with_extra_input(kv(0x15, b"\x51\xc0", b"\x00" * 32))
        with self.assertRaises(PsbtGuardError):
            parse_psbt(bad)

    def test_musig2_nonce_shape_is_checked(self):
        keydata = self.G + self.G
        good = self._v0_with_extra_input(kv(0x1b, b"\x11" * 66, keydata))
        self.assertEqual(parse_psbt(good).version, 0)
        bad = self._v0_with_extra_input(kv(0x1b, b"\x11" * 65, keydata))
        with self.assertRaises(PsbtGuardError):
            parse_psbt(bad)

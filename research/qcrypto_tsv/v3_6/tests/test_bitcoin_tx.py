from __future__ import annotations

import unittest

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.bitcoin_tx import (
    BitcoinTransaction,
    BitcoinTxError,
    TxInput,
    TxOutput,
    classify_script_pubkey,
    evaluate_serialized_transaction,
    parse_transaction,
    read_compact_size,
)

P2WPKH = bytes.fromhex("0014" + "11" * 20)
P2TR = bytes.fromhex("5120" + "22" * 32)
P2MR = bytes.fromhex("5220" + "33" * 32)


def unsigned_tx(script: bytes, *, value: int = 50_000) -> BitcoinTransaction:
    return BitcoinTransaction(
        version=2,
        inputs=(TxInput(prev_txid="44" * 32, vout=1, script_sig=b"", sequence=0xFFFFFFFD),),
        outputs=(TxOutput(value_sat=value, script_pubkey=script),),
        locktime=0,
        segwit=False,
    )


class BitcoinTxTests(unittest.TestCase):
    def test_roundtrip_and_txid_are_bound_to_actual_output_bytes(self):
        tx = unsigned_tx(P2WPKH)
        raw = tx.serialize()
        parsed = parse_transaction(raw)
        self.assertEqual(parsed.serialize(), raw)
        self.assertEqual(parsed.txid, tx.txid)
        self.assertEqual(parsed.outputs[0].script_type, "P2WPKH")

    def test_segwit_witness_roundtrip(self):
        tx = BitcoinTransaction(
            version=2,
            inputs=(TxInput(prev_txid="55" * 32, vout=0, script_sig=b"", sequence=1, witness=(b"sig", b"key")),),
            outputs=(TxOutput(value_sat=1, script_pubkey=P2WPKH),),
            locktime=0,
            segwit=True,
        )
        parsed = parse_transaction(tx.serialize())
        self.assertTrue(parsed.segwit)
        self.assertEqual(parsed.inputs[0].witness, (b"sig", b"key"))
        self.assertNotEqual(parsed.txid, parsed.wtxid)

    def test_nonminimal_compact_size_rejected(self):
        with self.assertRaises(BitcoinTxError):
            read_compact_size(b"\xfd\xfc\x00")

    def test_common_script_types_are_classified_from_bytes(self):
        self.assertEqual(classify_script_pubkey(P2WPKH), "P2WPKH")
        self.assertEqual(classify_script_pubkey(P2TR), "P2TR")
        self.assertEqual(classify_script_pubkey(P2MR), "P2MR")
        self.assertEqual(classify_script_pubkey(bytes.fromhex("76a914" + "00" * 20 + "88ac")), "P2PKH")
        self.assertEqual(classify_script_pubkey(bytes.fromhex("a914" + "00" * 20 + "87")), "P2SH")

    def test_mainnet_is_rejected_from_serialized_bytes(self):
        report = evaluate_serialized_transaction(
            unsigned_tx(P2WPKH).serialize(), network="MAINNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED
        )
        self.assertFalse(report.allowed)

    def test_hybrid_policy_rejects_p2tr_and_accepts_hidden_key_output_with_pq_binding(self):
        blocked = evaluate_serialized_transaction(
            unsigned_tx(P2TR).serialize(),
            network="SIGNET",
            policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            pq_recovery_output_indexes={0},
        )
        self.assertFalse(blocked.allowed)
        allowed = evaluate_serialized_transaction(
            unsigned_tx(P2WPKH).serialize(),
            network="SIGNET",
            policy_state=CryptoPolicyState.HYBRID_REQUIRED,
            pq_recovery_output_indexes={0},
        )
        self.assertTrue(allowed.allowed)

    def test_populated_scriptsig_is_refused_as_presign_transaction(self):
        tx = BitcoinTransaction(
            version=2,
            inputs=(TxInput(prev_txid="66" * 32, vout=0, script_sig=b"\x01\x01", sequence=0xFFFFFFFF),),
            outputs=(TxOutput(value_sat=1, script_pubkey=P2WPKH),),
            locktime=0,
            segwit=False,
        )
        report = evaluate_serialized_transaction(
            tx.serialize(), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED
        )
        self.assertFalse(report.allowed)
        self.assertTrue(any("not unsigned" in r for r in report.reasons))

    def test_p2mr_draft_output_stays_rejected_by_high_level_policy(self):
        report = evaluate_serialized_transaction(
            unsigned_tx(P2MR).serialize(), network="SIGNET", policy_state=CryptoPolicyState.ECDSA_ALLOWED
        )
        self.assertFalse(report.allowed)


if __name__ == "__main__":
    unittest.main()

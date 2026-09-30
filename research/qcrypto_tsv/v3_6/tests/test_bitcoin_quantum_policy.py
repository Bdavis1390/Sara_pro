from __future__ import annotations

import unittest

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import (
    CryptoPolicyState,
    ExposureClass,
    ProposedOutput,
    UtxoRecord,
    assess_utxo,
    build_migration_manifest,
    evaluate_new_output,
)

TXA = "11" * 32
TXB = "22" * 32
TXC = "33" * 32
TXD = "44" * 32


class BitcoinQuantumPolicyTests(unittest.TestCase):
    def test_p2tr_and_p2pk_are_long_exposure(self):
        for script in ("P2TR", "P2PK", "P2MS"):
            a = assess_utxo(UtxoRecord(txid=TXA, vout=0, amount_sat=1, script_type=script))
            self.assertEqual(a.exposure, ExposureClass.EXPOSED_LONG)
            self.assertIn("PRIORITIZE_MIGRATION", a.actions)

    def test_hash_hidden_output_becomes_reuse_exposed(self):
        clean = assess_utxo(UtxoRecord(txid=TXA, vout=1, amount_sat=2, script_type="P2WPKH"))
        reused = assess_utxo(UtxoRecord(txid=TXB, vout=1, amount_sat=2, script_type="P2WPKH", address_reused=True))
        self.assertEqual(clean.exposure, ExposureClass.HIDDEN_UNTIL_SPEND)
        self.assertEqual(reused.exposure, ExposureClass.CONDITIONAL_REUSE_EXPOSURE)
        self.assertGreater(reused.priority, clean.priority)

    def test_p2mr_is_never_mislabeled_as_active_consensus(self):
        a = assess_utxo(UtxoRecord(txid=TXC, vout=0, amount_sat=3, script_type="P2MR"))
        self.assertEqual(a.exposure, ExposureClass.PROPOSED_LONG_EXPOSURE_RESISTANT)
        self.assertTrue(a.consensus_feature_required)
        self.assertIn("TEST_ONLY_UNTIL_CONSENSUS_ACTIVATION", a.actions)

    def test_manifest_prioritizes_exposed_value(self):
        m = build_migration_manifest([
            UtxoRecord(txid=TXA, vout=0, amount_sat=1000, script_type="P2WPKH"),
            UtxoRecord(txid=TXB, vout=0, amount_sat=2000, script_type="P2TR"),
        ])
        self.assertEqual(m["utxos"][0]["txid"], TXB)
        self.assertEqual(m["totals"]["long_or_reuse_exposed_sat"], 2000)
        self.assertEqual(m["consensus_claim"], "NONE_LOCAL_POLICY_ONLY")

    def test_mainnet_and_unknown_network_are_hard_blocked(self):
        for network in ("MAINNET", "MYSTERY"):
            d = evaluate_new_output(
                ProposedOutput(network=network, script_type="P2WPKH"),
                CryptoPolicyState.ECDSA_ALLOWED,
            )
            self.assertFalse(d.allowed)

    def test_hybrid_required_blocks_long_exposure_and_requires_pq_path(self):
        blocked = evaluate_new_output(
            ProposedOutput(network="SIGNET", script_type="P2TR", has_pq_recovery_path=True),
            CryptoPolicyState.HYBRID_REQUIRED,
        )
        self.assertFalse(blocked.allowed)
        missing = evaluate_new_output(
            ProposedOutput(network="SIGNET", script_type="P2WPKH", has_pq_recovery_path=False),
            CryptoPolicyState.HYBRID_REQUIRED,
        )
        self.assertFalse(missing.allowed)
        allowed = evaluate_new_output(
            ProposedOutput(network="SIGNET", script_type="P2WPKH", has_pq_recovery_path=True),
            CryptoPolicyState.HYBRID_REQUIRED,
        )
        self.assertTrue(allowed.allowed)

    def test_pq_required_fails_closed_until_bitcoin_has_activated_pq_path(self):
        d = evaluate_new_output(
            ProposedOutput(network="SIGNET", script_type="P2WPKH", has_pq_recovery_path=True),
            CryptoPolicyState.PQ_REQUIRED,
        )
        self.assertFalse(d.allowed)
        self.assertIn("NO_CURRENT_ACTIVATED_BITCOIN_PQ_OUTPUT", d.required_controls)


if __name__ == "__main__":
    unittest.main()

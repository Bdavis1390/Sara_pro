import unittest

from bitcoin_qsb_mainnet_readiness import MainnetPQCProofEvidence, assess_mainnet_pqc_proof


class BitcoinQSBMainnetReadinessTests(unittest.TestCase):
    def test_qsb_mainnet_proof_is_real_but_not_network_wide_migration(self):
        qsb = MainnetPQCProofEvidence(
            name="QSB mainnet demonstration",
            source="https://starkware.co/blog/the-first-quantum-safe-bitcoin-transaction-has-been-mined/",
            mainnet_confirmed=True,
            consensus_change_required=False,
            standard_relay=False,
            direct_miner_path_required=True,
            protects_previously_exposed_pubkeys=False,
            production_wallet_support=False,
            network_wide_migration_path=False,
            independent_security_review_complete=False,
        )
        result = assess_mainnet_pqc_proof(qsb)
        self.assertEqual(result.maturity_state, "CONSENSUS_COMPATIBLE_MAINNET_PROOF")
        self.assertEqual(result.deployment_scope, "NONSTANDARD_DIRECT_MINER_PATH")
        self.assertEqual(result.migration_value, "DEMONSTRATED_OPT_IN_PREPOSITIONING_PATH")
        self.assertEqual(result.urgency, "INTEGRATE_INTO_MIGRATION_PLANNING_AND_REVIEW")
        self.assertTrue(any("ordinary mempool" in gap for gap in result.blocking_gaps))
        self.assertTrue(any("already exposed" in gap for gap in result.blocking_gaps))
        self.assertTrue(any("network-wide" in gap for gap in result.blocking_gaps))

    def test_mainnet_confirmation_does_not_imply_standard_relay_or_wallet_support(self):
        qsb = MainnetPQCProofEvidence(
            name="QSB",
            source="test",
            mainnet_confirmed=True,
            consensus_change_required=False,
            direct_miner_path_required=True,
        )
        result = assess_mainnet_pqc_proof(qsb)
        self.assertNotEqual(result.deployment_scope, "STANDARD_RELAY_CAPABLE")
        self.assertGreaterEqual(len(result.blocking_gaps), 3)

    def test_standardized_future_path_can_be_classified_separately(self):
        future = MainnetPQCProofEvidence(
            name="future mature path",
            source="test",
            mainnet_confirmed=True,
            consensus_change_required=False,
            standard_relay=True,
            protects_previously_exposed_pubkeys=True,
            production_wallet_support=True,
            network_wide_migration_path=True,
            independent_security_review_complete=True,
        )
        result = assess_mainnet_pqc_proof(future)
        self.assertEqual(result.deployment_scope, "STANDARD_RELAY_CAPABLE")
        self.assertEqual(result.blocking_gaps, ())


if __name__ == "__main__":
    unittest.main()

import unittest

from preprotocol_pq_vault import ChainVaultEvidence, assess_chain_vault, assess_portfolio


class PreProtocolPQVaultTests(unittest.TestCase):
    def test_algorand_native_pq_account_path(self):
        result = assess_chain_vault(ChainVaultEvidence(
            chain="Algorand",
            source="official mainnet documentation",
            native_pq_account_live=True,
            pq_authorization_live=True,
            standard_relay_or_wallet_flow=True,
            independent_security_review_complete=False,
            consensus_layer_pq=False,
        ))
        self.assertEqual(result.protection_state, "NATIVE_PQ_ACCOUNT_PATH")
        self.assertEqual(result.deployment_state, "MAINNET_PQ_AUTHORIZATION_AVAILABLE")
        self.assertNotEqual(result.residual_risk, "FULL_PROTOCOL_PQ")

    def test_bitcoin_qsb_is_preprotocol_not_full_protocol(self):
        result = assess_chain_vault(ChainVaultEvidence(
            chain="Bitcoin",
            source="QSB mainnet demonstration",
            mainnet_pq_vault_or_proof_live=True,
            pq_authorization_live=True,
            standard_relay_or_wallet_flow=False,
            exposed_key_rescue=False,
            consensus_layer_pq=False,
        ))
        self.assertEqual(result.protection_state, "PRE_PROTOCOL_PQ_VAULT_PATH")
        self.assertTrue(any("relay" in gap.lower() for gap in result.blocking_gaps))
        self.assertTrue(any("exposed" in gap.lower() for gap in result.blocking_gaps))

    def test_solana_project_reported_vault_requires_review(self):
        result = assess_chain_vault(ChainVaultEvidence(
            chain="Solana",
            source="project-reported Qubit mainnet deployment",
            mainnet_pq_vault_or_proof_live=True,
            pq_authorization_live=True,
            standard_relay_or_wallet_flow=True,
            independent_security_review_complete=False,
            consensus_layer_pq=False,
        ))
        self.assertEqual(result.protection_state, "PRE_PROTOCOL_PQ_VAULT_PATH")
        self.assertTrue(any("Independent security review" in gap for gap in result.blocking_gaps))

    def test_ethereum_audited_substrate_does_not_equal_live_pq_validator(self):
        result = assess_chain_vault(ChainVaultEvidence(
            chain="Ethereum",
            source="Project Eleven audited ERC-4337 reference implementation",
            programmable_account_substrate_live=True,
            audited_reference_implementation=True,
            pq_authorization_live=False,
            standard_relay_or_wallet_flow=True,
            consensus_layer_pq=False,
            independent_security_review_complete=True,
        ))
        self.assertEqual(result.protection_state, "AUDITED_CRYPTO_AGILE_ACCOUNT_SUBSTRATE")
        self.assertEqual(result.deployment_state, "PQ_AUTHORIZATION_INTEGRATION_PENDING")

    def test_portfolio_state_requires_real_paths(self):
        algo = assess_chain_vault(ChainVaultEvidence(
            chain="Algorand", source="test", native_pq_account_live=True,
            pq_authorization_live=True, standard_relay_or_wallet_flow=True,
        ))
        btc = assess_chain_vault(ChainVaultEvidence(
            chain="Bitcoin", source="test", mainnet_pq_vault_or_proof_live=True,
            pq_authorization_live=True,
        ))
        eth = assess_chain_vault(ChainVaultEvidence(
            chain="Ethereum", source="test", programmable_account_substrate_live=True,
            audited_reference_implementation=True,
        ))
        self.assertEqual(
            assess_portfolio([algo, btc, eth]),
            "INCREMENTAL_MULTI_CHAIN_PQ_ASSET_PROTECTION_AVAILABLE",
        )


if __name__ == "__main__":
    unittest.main()

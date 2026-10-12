import unittest

from authority_abstraction_convergence import (
    AuthorityAbstractionEvidence,
    assess_authority_abstraction,
    assess_cross_chain_convergence,
)


class AuthorityAbstractionConvergenceTests(unittest.TestCase):
    def test_algorand_live_pq_rekey_path(self):
        result = assess_authority_abstraction(
            AuthorityAbstractionEvidence(
                chain="Algorand",
                stable_authority_identifier=True,
                authenticator_replaceable_without_asset_move=True,
                pq_authentication_live=True,
                programmable_or_scheme_agile_validation=True,
                migration_path_live=True,
                recovery_compatible=True,
            )
        )
        self.assertEqual(result.maturity, "LIVE_PQ_AUTHORITY_ABSTRACTION")

    def test_sui_alias_substrate_is_not_promoted_to_live_pq_account(self):
        result = assess_authority_abstraction(
            AuthorityAbstractionEvidence(
                chain="Sui",
                stable_authority_identifier=True,
                authenticator_replaceable_without_asset_move=True,
                pq_authentication_live=False,
                programmable_or_scheme_agile_validation=True,
                migration_path_live=False,
                roadmap_only=True,
                recovery_compatible=True,
            )
        )
        self.assertEqual(result.maturity, "LIVE_AGILITY_SUBSTRATE_PQ_PATH_PENDING")

    def test_ethereum_draft_native_aa_remains_roadmap_state(self):
        result = assess_authority_abstraction(
            AuthorityAbstractionEvidence(
                chain="Ethereum",
                stable_authority_identifier=False,
                authenticator_replaceable_without_asset_move=False,
                pq_authentication_live=False,
                programmable_or_scheme_agile_validation=True,
                migration_path_live=False,
                roadmap_only=True,
                recovery_compatible=True,
            )
        )
        self.assertEqual(result.maturity, "DRAFT_NATIVE_AUTHORITY_ABSTRACTION")

    def test_three_ecosystem_pattern_triggers_convergence(self):
        assessments = [
            assess_authority_abstraction(
                AuthorityAbstractionEvidence(
                    chain="Algorand",
                    stable_authority_identifier=True,
                    authenticator_replaceable_without_asset_move=True,
                    pq_authentication_live=True,
                    programmable_or_scheme_agile_validation=True,
                    migration_path_live=True,
                    recovery_compatible=True,
                )
            ),
            assess_authority_abstraction(
                AuthorityAbstractionEvidence(
                    chain="Sui",
                    stable_authority_identifier=True,
                    authenticator_replaceable_without_asset_move=True,
                    programmable_or_scheme_agile_validation=True,
                    roadmap_only=True,
                    recovery_compatible=True,
                )
            ),
            assess_authority_abstraction(
                AuthorityAbstractionEvidence(
                    chain="Ethereum",
                    programmable_or_scheme_agile_validation=True,
                    roadmap_only=True,
                    recovery_compatible=True,
                )
            ),
        ]
        self.assertEqual(
            assess_cross_chain_convergence(assessments),
            "CROSS_CHAIN_AUTHORITY_ABSTRACTION_CONVERGENCE",
        )

    def test_account_agility_never_implies_pq_consensus(self):
        result = assess_authority_abstraction(
            AuthorityAbstractionEvidence(
                chain="Algorand",
                stable_authority_identifier=True,
                authenticator_replaceable_without_asset_move=True,
                pq_authentication_live=True,
                programmable_or_scheme_agile_validation=True,
                migration_path_live=True,
                recovery_compatible=True,
                consensus_layer_pq=False,
            )
        )
        self.assertTrue(any("consensus" in risk.lower() for risk in result.residual_risks))


if __name__ == "__main__":
    unittest.main()

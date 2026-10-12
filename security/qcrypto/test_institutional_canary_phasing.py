import unittest

from institutional_canary_phasing import InstitutionalCanaryEvidence, assess_institutional_canary


class InstitutionalCanaryPhasingTests(unittest.TestCase):
    def test_native_pq_account_is_phase_a_not_institution_grade(self):
        result = assess_institutional_canary(
            InstitutionalCanaryEvidence(
                native_pq_account_live=True,
                wallet_tooling_live=True,
                bounded_single_account_controls_validated=True,
                explicit_human_approval_required=True,
            )
        )
        self.assertEqual(result.phase, "PHASE_A_BOUNDED_NATIVE_PQ_CANARY")
        self.assertEqual(result.deployment_class, "SINGLE_ACCOUNT_PQ_AUTHORIZATION_ONLY")

    def test_roadmap_multisig_does_not_promote_phase_b(self):
        result = assess_institutional_canary(
            InstitutionalCanaryEvidence(
                native_pq_account_live=True,
                wallet_tooling_live=True,
                bounded_single_account_controls_validated=True,
                native_multi_crypto_policy_live=False,
                weighted_or_multi_approver_policy_live=False,
                explicit_human_approval_required=True,
            )
        )
        self.assertNotEqual(result.phase, "PHASE_B_INSTITUTIONAL_CANARY_READY")

    def test_phase_b_requires_live_policy_review_and_recovery(self):
        result = assess_institutional_canary(
            InstitutionalCanaryEvidence(
                native_pq_account_live=True,
                wallet_tooling_live=True,
                bounded_single_account_controls_validated=True,
                native_multi_crypto_policy_live=True,
                weighted_or_multi_approver_policy_live=True,
                hybrid_classical_pq_policy_supported=True,
                policy_interop_validated=True,
                independent_review_complete=False,
                recovery_drill_passed=True,
                explicit_human_approval_required=True,
            )
        )
        self.assertNotEqual(result.phase, "PHASE_B_INSTITUTIONAL_CANARY_READY")

    def test_full_phase_b_is_still_human_gated(self):
        result = assess_institutional_canary(
            InstitutionalCanaryEvidence(
                native_pq_account_live=True,
                wallet_tooling_live=True,
                bounded_single_account_controls_validated=True,
                native_multi_crypto_policy_live=True,
                weighted_or_multi_approver_policy_live=True,
                hybrid_classical_pq_policy_supported=True,
                policy_interop_validated=True,
                independent_review_complete=True,
                recovery_drill_passed=True,
                explicit_human_approval_required=True,
            )
        )
        self.assertEqual(result.phase, "PHASE_B_INSTITUTIONAL_CANARY_READY")
        self.assertIn("EXPLICIT_AUTHORIZATION", result.action)

    def test_phase_b_never_implies_pq_consensus(self):
        result = assess_institutional_canary(
            InstitutionalCanaryEvidence(
                native_pq_account_live=True,
                wallet_tooling_live=True,
                bounded_single_account_controls_validated=True,
                native_multi_crypto_policy_live=True,
                weighted_or_multi_approver_policy_live=True,
                hybrid_classical_pq_policy_supported=True,
                policy_interop_validated=True,
                independent_review_complete=True,
                recovery_drill_passed=True,
                explicit_human_approval_required=True,
                consensus_layer_pq=False,
            )
        )
        self.assertTrue(any("consensus" in gap.lower() for gap in result.blockers))


if __name__ == "__main__":
    unittest.main()

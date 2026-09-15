import unittest

from quantum_continuity_envelope import ContinuityEnvelopeEvidence, assess_continuity_envelope


class QuantumContinuityEnvelopeTests(unittest.TestCase):
    def test_full_envelope_is_pilot_ready_but_not_full_protocol_pq(self):
        evidence = ContinuityEnvelopeEvidence(
            name="reviewed dual-family envelope",
            source="test",
            programmable_enforcement_layer=True,
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_threshold_gate=True,
            pq_member_authentication_available=True,
            independent_pq_families_available=True,
            precommitted_recovery_path=True,
            independent_review_complete=True,
            chain_native_pq_consensus=False,
        )
        result = assess_continuity_envelope(evidence)
        self.assertEqual(result.authorization_state, "AUTHORIZATION_VIRTUALIZED")
        self.assertEqual(result.algorithm_state, "ALGORITHM_DIVERSE_PQ_AUTH_AVAILABLE")
        self.assertEqual(result.operational_state, "QCE_PILOT_READY")
        self.assertTrue(any("Base-layer consensus" in item for item in result.residual_risks))

    def test_threshold_policy_can_be_ready_without_native_pq_consensus(self):
        evidence = ContinuityEnvelopeEvidence(
            name="programmable vault",
            source="test",
            programmable_enforcement_layer=True,
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_threshold_gate=True,
            pq_member_authentication_available=True,
            independent_pq_families_available=True,
            precommitted_recovery_path=True,
        )
        result = assess_continuity_envelope(evidence)
        self.assertEqual(result.operational_state, "QCE_INTEGRATION_CANDIDATE_REVIEW_REQUIRED")
        self.assertNotEqual(result.operational_state, "QCE_PILOT_READY")

    def test_stateful_signing_without_single_use_controls_is_blocked(self):
        evidence = ContinuityEnvelopeEvidence(
            name="stateful threshold signer",
            source="test",
            programmable_enforcement_layer=True,
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_threshold_gate=True,
            pq_member_authentication_available=True,
            independent_pq_families_available=True,
            precommitted_recovery_path=True,
            stateful_signing_present=True,
            state_reuse_controls_verified=False,
        )
        result = assess_continuity_envelope(evidence)
        self.assertEqual(result.operational_state, "BLOCKED_STATE_REUSE_RISK")
        self.assertEqual(result.migration_action, "FIX_STATE_CONSUMPTION_AND_RETRY_SAFETY_BEFORE_DEPLOYMENT")

    def test_single_family_pq_does_not_count_as_algorithm_diverse(self):
        evidence = ContinuityEnvelopeEvidence(
            name="single family",
            source="test",
            programmable_enforcement_layer=True,
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_threshold_gate=True,
            pq_member_authentication_available=True,
            independent_pq_families_available=False,
            precommitted_recovery_path=True,
        )
        result = assess_continuity_envelope(evidence)
        self.assertEqual(result.algorithm_state, "SINGLE_FAMILY_PQ_AUTH_AVAILABLE")
        self.assertNotEqual(result.operational_state, "QCE_PILOT_READY")

    def test_crypto_agile_account_substrate_is_not_qce_until_threshold_and_recovery_exist(self):
        evidence = ContinuityEnvelopeEvidence(
            name="account abstraction only",
            source="test",
            programmable_enforcement_layer=True,
            stable_authority_identifier=True,
            replaceable_authenticator=True,
        )
        result = assess_continuity_envelope(evidence)
        self.assertEqual(result.authorization_state, "CRYPTO_AGILE_AUTH_SUBSTRATE")
        self.assertEqual(result.operational_state, "QCE_SUBSTRATE_READY_PQ_INTEGRATION_PENDING")


if __name__ == "__main__":
    unittest.main()

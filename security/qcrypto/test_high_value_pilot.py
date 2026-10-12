import unittest

from high_value_pilot import HighValuePilotEvidence, assess_high_value_pilot


class HighValuePilotTests(unittest.TestCase):
    def test_dual_family_provider_diversity_is_recognized_without_authorizing_value(self):
        evidence = HighValuePilotEvidence(
            name="dual-provider signer lab",
            source="test",
            hardware_backed_ml_dsa_available=True,
            hardware_backed_slh_dsa_available=True,
            provider_diversity_available=True,
            immutable_evidence_logging=True,
            human_approval_required=True,
        )
        result = assess_high_value_pilot(evidence)
        self.assertEqual(result.signer_state, "DUAL_FAMILY_DUAL_PROVIDER_PQ_SIGNING_AVAILABLE")
        self.assertNotEqual(result.pilot_state, "HVP_BOUNDED_CANARY_READY")

    def test_testnet_requires_authorization_recovery_and_chain_adapter(self):
        evidence = HighValuePilotEvidence(
            name="testnet candidate",
            source="test",
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_quorum=True,
            fail_closed_classical_bypass=True,
            hardware_backed_ml_dsa_available=True,
            hardware_backed_slh_dsa_available=True,
            provider_diversity_available=True,
            chain_adapter_testnet_validated=True,
            precommitted_recovery=True,
            immutable_evidence_logging=True,
            human_approval_required=True,
        )
        result = assess_high_value_pilot(evidence)
        self.assertEqual(result.pilot_state, "HVP_TESTNET_READY")

    def test_canary_controls_do_not_bypass_explicit_human_authorization(self):
        evidence = HighValuePilotEvidence(
            name="reviewed pilot",
            source="test",
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_quorum=True,
            fail_closed_classical_bypass=True,
            hardware_backed_ml_dsa_available=True,
            hardware_backed_slh_dsa_available=True,
            provider_diversity_available=True,
            chain_adapter_testnet_validated=True,
            precommitted_recovery=True,
            recovery_drill_passed=True,
            immutable_evidence_logging=True,
            human_approval_required=True,
            independent_review_complete=True,
            bounded_value_policy_defined=True,
            live_value_canary_authorized=False,
        )
        result = assess_high_value_pilot(evidence)
        self.assertEqual(result.pilot_state, "HVP_BOUNDED_CANARY_READY_PENDING_HUMAN_AUTHORIZATION")
        self.assertEqual(result.deployment_action, "HOLD_LIVE_VALUE; COMPLETE_APPROVAL_AND_CHANGE_CONTROL")

    def test_canary_ready_still_does_not_claim_full_protocol_pq(self):
        evidence = HighValuePilotEvidence(
            name="authorized canary",
            source="test",
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_quorum=True,
            fail_closed_classical_bypass=True,
            hardware_backed_ml_dsa_available=True,
            hardware_backed_slh_dsa_available=True,
            provider_diversity_available=True,
            chain_adapter_testnet_validated=True,
            precommitted_recovery=True,
            recovery_drill_passed=True,
            immutable_evidence_logging=True,
            human_approval_required=True,
            independent_review_complete=True,
            bounded_value_policy_defined=True,
            live_value_canary_authorized=True,
            chain_native_pq_consensus=False,
        )
        result = assess_high_value_pilot(evidence)
        self.assertEqual(result.pilot_state, "HVP_BOUNDED_CANARY_READY")
        self.assertTrue(any("base-layer consensus" in item for item in result.blockers))

    def test_recovery_drill_is_required_for_bounded_canary(self):
        evidence = HighValuePilotEvidence(
            name="missing recovery drill",
            source="test",
            stable_authority_identifier=True,
            replaceable_authenticator=True,
            signature_agnostic_quorum=True,
            fail_closed_classical_bypass=True,
            hardware_backed_ml_dsa_available=True,
            hardware_backed_slh_dsa_available=True,
            provider_diversity_available=True,
            chain_adapter_testnet_validated=True,
            precommitted_recovery=True,
            recovery_drill_passed=False,
            immutable_evidence_logging=True,
            human_approval_required=True,
            independent_review_complete=True,
            bounded_value_policy_defined=True,
        )
        result = assess_high_value_pilot(evidence)
        self.assertEqual(result.pilot_state, "HVP_TESTNET_READY")


if __name__ == "__main__":
    unittest.main()

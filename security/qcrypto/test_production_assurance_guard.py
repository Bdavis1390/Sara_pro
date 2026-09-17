import unittest

from production_assurance_guard import ProductionEvidence, assess_production


class ProductionAssuranceGuardTests(unittest.TestCase):
    def test_kms_contract_cannot_promote_unrelated_claims(self):
        result = assess_production(ProductionEvidence(provider_adapter_contract_passed=True))
        self.assertEqual(result.hsm_kms_state, "PROVIDER_ADAPTER_IMPLEMENTED_NOT_LIVE_INTEGRATED")
        self.assertEqual(result.fips_state, "FIPS_VALIDATION_NOT_ESTABLISHED")
        self.assertFalse(result.bitcoin_native_signing_claim)
        self.assertFalse(result.ethereum_native_signing_claim)
        self.assertFalse(result.broadcast_claim)
        self.assertFalse(result.mainnet_authority_claim)
        self.assertFalse(result.real_value_movement_claim)
        self.assertFalse(result.federal_compliance_claim)
        self.assertFalse(result.independent_validation_claim)
        self.assertFalse(result.end_to_end_pq_cryptocurrency_security_claim)

    def test_active_cmvp_certificate_without_algorithm_scope_cannot_promote_fips_state(self):
        result = assess_production(
            ProductionEvidence(
                provider_adapter_contract_passed=True,
                live_hsm_kms_probe_passed=True,
                provider_fips_module_documented=True,
                provider_cmvp_certificate_active=True,
                provider_cmvp_algorithm_scope_verified=False,
            )
        )
        self.assertEqual(result.hsm_kms_state, "LIVE_HSM_KMS_INTEGRATION_OBSERVED")
        self.assertEqual(
            result.fips_state,
            "ACTIVE_PROVIDER_CMVP_CERTIFICATE_FOUND_ALGORITHM_SCOPE_NOT_VERIFIED",
        )

    def test_scope_verified_provider_does_not_make_worldshepherd_fips_validated(self):
        result = assess_production(
            ProductionEvidence(
                provider_adapter_contract_passed=True,
                live_hsm_kms_probe_passed=True,
                provider_fips_module_documented=True,
                provider_cmvp_certificate_active=True,
                provider_cmvp_algorithm_scope_verified=True,
            )
        )
        self.assertEqual(
            result.fips_state,
            "VALIDATED_PROVIDER_MODULE_AND_ALGORITHM_SCOPE_USED_NOT_WORLD_SHEPHERD_VALIDATED",
        )
        self.assertFalse(result.federal_compliance_claim)
        self.assertFalse(result.independent_validation_claim)

    def test_federal_mapping_without_authorized_complete_assessment_cannot_claim_compliance(self):
        partial = ProductionEvidence(
            federal_assessment_attributable=True,
            federal_scope_and_version_bound=True,
        )
        self.assertFalse(assess_production(partial).federal_compliance_claim)

        complete = ProductionEvidence(
            federal_assessment_attributable=True,
            federal_scope_and_version_bound=True,
            federal_assessor_authority_verified=True,
            federal_control_evidence_complete=True,
        )
        self.assertTrue(assess_production(complete).federal_compliance_claim)

    def test_native_signature_requires_exact_evidence_binding(self):
        unbound = assess_production(
            ProductionEvidence(bitcoin_native_signature_verified=True)
        )
        self.assertFalse(unbound.bitcoin_native_signing_claim)

        bound = assess_production(
            ProductionEvidence(
                bitcoin_native_signature_verified=True,
                native_execution_evidence_digest_bound=True,
            )
        )
        self.assertTrue(bound.bitcoin_native_signing_claim)
        self.assertFalse(bound.broadcast_claim)

    def test_mainnet_and_real_value_require_separate_evidence_layers(self):
        broadcast = assess_production(
            ProductionEvidence(
                bitcoin_native_signature_verified=True,
                native_execution_evidence_digest_bound=True,
                transaction_broadcast_receipt_verified=True,
                canonical_transaction_id_verified=True,
            )
        )
        self.assertTrue(broadcast.broadcast_claim)
        self.assertFalse(broadcast.mainnet_authority_claim)
        self.assertFalse(broadcast.real_value_movement_claim)

        mainnet = assess_production(
            ProductionEvidence(
                bitcoin_native_signature_verified=True,
                native_execution_evidence_digest_bound=True,
                transaction_broadcast_receipt_verified=True,
                canonical_transaction_id_verified=True,
                mainnet_authorization_recorded=True,
                mainnet_authority_issuer_verified=True,
            )
        )
        self.assertTrue(mainnet.mainnet_authority_claim)
        self.assertFalse(mainnet.real_value_movement_claim)

        not_independently_verified = assess_production(
            ProductionEvidence(
                bitcoin_native_signature_verified=True,
                native_execution_evidence_digest_bound=True,
                transaction_broadcast_receipt_verified=True,
                canonical_transaction_id_verified=True,
                mainnet_authorization_recorded=True,
                mainnet_authority_issuer_verified=True,
                real_value_execution_receipt_verified=True,
            )
        )
        self.assertFalse(not_independently_verified.real_value_movement_claim)

    def test_independent_validation_requires_identity_and_exact_artifact_binding(self):
        partial = assess_production(
            ProductionEvidence(independent_reproduction_recorded=True)
        )
        self.assertFalse(partial.independent_validation_claim)

        complete = assess_production(
            ProductionEvidence(
                independent_reproduction_recorded=True,
                independent_reviewer_identity_verified=True,
                independent_artifact_digest_bound=True,
            )
        )
        self.assertTrue(complete.independent_validation_claim)

    def test_end_to_end_pq_claim_requires_all_system_layers_and_independent_evidence(self):
        almost = ProductionEvidence(
            pq_transaction_authority_covered=True,
            pq_consensus_covered=True,
            pq_data_availability_covered=True,
            pq_bridge_custody_covered=True,
            pq_network_transport_covered=True,
            production_deployment_evidence=True,
            independent_reproduction_recorded=True,
            independent_reviewer_identity_verified=True,
            independent_artifact_digest_bound=False,
        )
        self.assertFalse(
            assess_production(almost).end_to_end_pq_cryptocurrency_security_claim
        )
        complete = ProductionEvidence(
            pq_transaction_authority_covered=True,
            pq_consensus_covered=True,
            pq_data_availability_covered=True,
            pq_bridge_custody_covered=True,
            pq_network_transport_covered=True,
            production_deployment_evidence=True,
            independent_reproduction_recorded=True,
            independent_reviewer_identity_verified=True,
            independent_artifact_digest_bound=True,
        )
        self.assertTrue(
            assess_production(complete).end_to_end_pq_cryptocurrency_security_claim
        )


if __name__ == "__main__":
    unittest.main()

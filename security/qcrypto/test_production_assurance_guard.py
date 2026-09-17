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

    def test_live_fips_backed_provider_does_not_make_worldshepherd_fips_validated(self):
        result = assess_production(
            ProductionEvidence(
                provider_adapter_contract_passed=True,
                live_hsm_kms_probe_passed=True,
                provider_fips_module_documented=True,
                provider_cmvp_certificate_active=True,
            )
        )
        self.assertEqual(result.hsm_kms_state, "LIVE_HSM_KMS_INTEGRATION_OBSERVED")
        self.assertEqual(
            result.fips_state,
            "VALIDATED_PROVIDER_MODULE_USED_NOT_WORLD_SHEPHERD_VALIDATED",
        )
        self.assertFalse(result.federal_compliance_claim)
        self.assertFalse(result.independent_validation_claim)

    def test_federal_mapping_without_attributable_assessment_cannot_claim_compliance(self):
        result = assess_production(
            ProductionEvidence(federal_scope_and_version_bound=True)
        )
        self.assertFalse(result.federal_compliance_claim)

    def test_mainnet_and_real_value_require_separate_broadcast_and_authority_evidence(self):
        broadcast_only = assess_production(
            ProductionEvidence(transaction_broadcast_receipt_verified=True)
        )
        self.assertTrue(broadcast_only.broadcast_claim)
        self.assertFalse(broadcast_only.mainnet_authority_claim)
        self.assertFalse(broadcast_only.real_value_movement_claim)

        authorized = assess_production(
            ProductionEvidence(
                transaction_broadcast_receipt_verified=True,
                mainnet_authorization_recorded=True,
            )
        )
        self.assertTrue(authorized.mainnet_authority_claim)
        self.assertFalse(authorized.real_value_movement_claim)

    def test_end_to_end_pq_claim_requires_all_system_layers_and_independent_evidence(self):
        almost = ProductionEvidence(
            pq_transaction_authority_covered=True,
            pq_consensus_covered=True,
            pq_data_availability_covered=True,
            pq_bridge_custody_covered=True,
            pq_network_transport_covered=True,
            production_deployment_evidence=True,
            independent_reproduction_recorded=False,
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
        )
        self.assertTrue(
            assess_production(complete).end_to_end_pq_cryptocurrency_security_claim
        )


if __name__ == "__main__":
    unittest.main()

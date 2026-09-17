import unittest

from institutional_custody_readiness import CustodyEvidence, assess_custody_readiness


class InstitutionalCustodyReadinessTests(unittest.TestCase):
    def test_regulated_custodian_with_live_controls_and_pq_pilot_is_not_chain_ready(self):
        evidence = CustodyEvidence(
            name="regulated custodian",
            source="public evidence",
            regulated=True,
            deployed_exposure_controls=True,
            pq_signing_simulation=True,
            pq_signing_live_chain=False,
            hybrid_transport_in_production=False,
            pq_hsm_or_signer_support=False,
            blockchain_pq_authorization_available=False,
            independent_review_complete=False,
        )
        result = assess_custody_readiness(evidence)
        self.assertEqual(result.custody_state, "REGULATED_CUSTODY_MIGRATION_OPERATIONALIZED")
        self.assertEqual(result.chain_dependency_state, "CHAIN_AUTHORIZATION_REMAINS_BOTTLENECK")
        self.assertEqual(result.urgency, "ACCELERATE_CHAIN_INTEGRATION_AND_INDEPENDENT_VALIDATION")

    def test_production_transport_readiness_does_not_imply_blockchain_pq_signing(self):
        evidence = CustodyEvidence(
            name="custody platform",
            source="public evidence",
            regulated=True,
            hybrid_transport_in_production=True,
            pq_hsm_or_signer_support=True,
        )
        result = assess_custody_readiness(evidence)
        self.assertEqual(result.custody_state, "PRODUCTION_MIGRATION_CONTROLS_PRESENT")
        self.assertNotEqual(result.chain_dependency_state, "CHAIN_AUTHORIZATION_PATH_AVAILABLE")

    def test_live_chain_path_requires_both_chain_support_and_live_signing(self):
        evidence = CustodyEvidence(
            name="future integrated custodian",
            source="test",
            regulated=True,
            deployed_exposure_controls=True,
            pq_signing_simulation=True,
            pq_signing_live_chain=True,
            pq_hsm_or_signer_support=True,
            blockchain_pq_authorization_available=True,
            independent_review_complete=True,
        )
        result = assess_custody_readiness(evidence)
        self.assertEqual(result.chain_dependency_state, "CHAIN_AUTHORIZATION_PATH_AVAILABLE")


if __name__ == "__main__":
    unittest.main()

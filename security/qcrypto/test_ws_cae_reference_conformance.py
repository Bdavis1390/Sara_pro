import unittest

from ws_cae_reference_conformance import WSCAEReferenceProfile, assess_reference_profile


class WSCAEReferenceConformanceTests(unittest.TestCase):
    def test_algorand_mainnet_pq_authority_remains_separate_from_consensus(self):
        result = assess_reference_profile(
            WSCAEReferenceProfile(
                ecosystem="Algorand",
                adapter_class="NATIVE_REKEY",
                implementation_maturity="MAINNET",
                stable_authority_id=True,
                authenticator_replaceable=True,
                pq_authorization_state="PQ_MAINNET",
                policy_state_documented=True,
                recovery_state_documented=True,
                domain_binding_documented=True,
                evidence_state_documented=True,
                consensus_pq_state="PQ_RESEARCH_OR_PARTIAL",
            )
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.authority_state, "AUTHORITY_ABSTRACTION_PRESENT")
        self.assertEqual(result.maturity_state, "IMPLEMENTATION_MAINNET")
        self.assertEqual(result.pq_authorization_state, "PQ_MAINNET")
        self.assertEqual(
            result.consensus_boundary,
            "ACCOUNT_AUTHORITY_RESULT_DOES_NOT_ESTABLISH_PQ_CONSENSUS",
        )

    def test_ethereum_eip8141_devnet_is_not_promoted_to_mainnet_or_pq_auth(self):
        result = assess_reference_profile(
            WSCAEReferenceProfile(
                ecosystem="Ethereum",
                adapter_class="NATIVE_ACCOUNT_ABSTRACTION",
                implementation_maturity="DEVNET",
                stable_authority_id=True,
                authenticator_replaceable=True,
                pq_authorization_state="PLUGGABLE_AUTH_ONLY",
                policy_state_documented=True,
                recovery_state_documented=False,
                domain_binding_documented=True,
                evidence_state_documented=True,
                consensus_pq_state="PQ_RESEARCH_OR_PARTIAL",
            )
        )
        self.assertTrue(result.valid)
        self.assertEqual(result.authority_state, "AUTHORITY_ABSTRACTION_PRESENT")
        self.assertEqual(result.maturity_state, "IMPLEMENTATION_DEVNET")
        self.assertEqual(result.pq_authorization_state, "PLUGGABLE_AUTH_ONLY")
        self.assertNotEqual(result.maturity_state, "IMPLEMENTATION_MAINNET")
        self.assertEqual(
            result.consensus_boundary,
            "ACCOUNT_AUTHORITY_RESULT_DOES_NOT_ESTABLISH_PQ_CONSENSUS",
        )

    def test_invalid_maturity_fails_closed(self):
        result = assess_reference_profile(
            WSCAEReferenceProfile(
                ecosystem="Example",
                adapter_class="OTHER_REVIEW_REQUIRED",
                implementation_maturity="PRODUCTIONISH",
                stable_authority_id=True,
                authenticator_replaceable=True,
                pq_authorization_state="NONE",
                policy_state_documented=False,
                recovery_state_documented=False,
                domain_binding_documented=True,
                evidence_state_documented=True,
            )
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.maturity_state, "IMPLEMENTATION_STATE_INVALID")

    def test_missing_domain_or_evidence_binding_fails_closed(self):
        result = assess_reference_profile(
            WSCAEReferenceProfile(
                ecosystem="Example",
                adapter_class="ADDRESS_ALIAS",
                implementation_maturity="TESTNET",
                stable_authority_id=True,
                authenticator_replaceable=True,
                pq_authorization_state="PQ_NON_MAINNET",
                policy_state_documented=True,
                recovery_state_documented=True,
                domain_binding_documented=False,
                evidence_state_documented=False,
            )
        )
        self.assertFalse(result.valid)
        self.assertGreaterEqual(len(result.issues), 2)


if __name__ == "__main__":
    unittest.main()

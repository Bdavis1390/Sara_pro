import unittest

from ws_cae_consumer_policy import WSCAEConsumerPolicy, assess_consumer_policy
from ws_cae_reference_conformance import WSCAEReferenceProfile, assess_reference_profile


class WSCAEConsumerPolicyTests(unittest.TestCase):
    def profile(self, **overrides):
        data = dict(
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
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
        )
        data.update(overrides)
        return WSCAEReferenceProfile(**data)

    def policy(self, **overrides):
        data = dict(
            name="institutional-authority-minimum",
            minimum_maturity="MAINNET",
            accepted_pq_authorization_states=("PQ_MAINNET",),
            accepted_consensus_states=("CLASSICAL_OR_UNPROVEN", "PQ_RESEARCH_OR_PARTIAL", "PQ_DEPLOYED"),
            require_stable_authority_id=True,
            require_authenticator_replaceable=True,
            require_policy_state_documented=True,
            require_recovery_state_documented=True,
            require_domain_binding_documented=True,
            require_evidence_state_documented=True,
        )
        data.update(overrides)
        return WSCAEConsumerPolicy(**data)

    def test_mainnet_pq_authority_can_pass_without_claiming_pq_consensus(self):
        profile = self.profile()
        result = assess_consumer_policy(profile, assess_reference_profile(profile), self.policy())
        self.assertTrue(result.passed)

    def test_devnet_pluggable_auth_fails_mainnet_pq_policy(self):
        profile = self.profile(
            ecosystem="Ethereum",
            implementation_maturity="DEVNET",
            pq_authorization_state="PLUGGABLE_AUTH_ONLY",
        )
        result = assess_consumer_policy(profile, assess_reference_profile(profile), self.policy())
        self.assertFalse(result.passed)
        self.assertTrue(any("maturity" in failure for failure in result.failures))
        self.assertTrue(any("PQ authorization" in failure for failure in result.failures))

    def test_policy_can_require_recovery_without_redefining_chain_profile(self):
        profile = self.profile(recovery_state_documented=False)
        result = assess_consumer_policy(profile, assess_reference_profile(profile), self.policy())
        self.assertFalse(result.passed)
        self.assertTrue(any("recovery" in failure for failure in result.failures))

    def test_invalid_policy_fails_closed(self):
        profile = self.profile()
        result = assess_consumer_policy(
            profile,
            assess_reference_profile(profile),
            self.policy(minimum_maturity="PRODUCTIONISH"),
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("minimum_maturity" in failure for failure in result.failures))


if __name__ == "__main__":
    unittest.main()

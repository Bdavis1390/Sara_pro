import unittest

from bitcoin_mitigation_readiness import MitigationEvidence, assess_bitcoin_mitigation_stack


class BitcoinMitigationReadinessTests(unittest.TestCase):
    def test_draft_signature_plus_rescue_and_sunset_is_research_stack_not_deployable(self):
        shrincs = MitigationEvidence(
            name="SHRINCS",
            source="https://github.com/SHRINCS/shrincs-bip/blob/main/SHRINCS.md",
            role="pq_authorization",
            status="Draft",
            reference_implementation=True,
            security_proof_complete=False,
            test_vectors_complete=False,
            production_implementation=False,
            consensus_activated=False,
            stateful_primary=True,
            stateless_fallback=True,
        )
        dropkick = MitigationEvidence(
            name="DropKick",
            source="https://conduition.io/bitcoin/dropkick/",
            role="rescue",
            status="Proposal",
            requires_pq_authorization=True,
        )
        bip361 = MitigationEvidence(
            name="BIP-361",
            source="https://github.com/bitcoin/bips/blob/master/bip-0361.mediawiki",
            role="sunset",
            status="Draft",
            requires_pq_authorization=True,
        )

        result = assess_bitcoin_mitigation_stack(shrincs, dropkick, bip361)
        self.assertEqual(result.pq_authorization_state, "PQ_AUTHORIZATION_EXECUTABLE_DRAFT")
        self.assertEqual(result.rescue_state, "RESCUE_BLOCKED_ON_PQ_AUTHORIZATION")
        self.assertEqual(result.sunset_state, "SUNSET_BLOCKED_ON_PQ_AUTHORIZATION")
        self.assertEqual(result.deployment_state, "DEPENDENCY_COMPLETE_RESEARCH_STACK")
        self.assertEqual(result.urgency, "ACCELERATE_SECURITY_PROOF_INTEROP_AND_ACTIVATION_PLANNING")
        self.assertTrue(any("security proof" in gap.lower() for gap in result.blocking_gaps))
        self.assertTrue(any("test vectors" in gap.lower() for gap in result.blocking_gaps))

    def test_reference_implementation_never_equals_consensus_activation(self):
        pq = MitigationEvidence(
            name="draft PQ",
            source="test",
            role="pq_authorization",
            status="Draft",
            reference_implementation=True,
        )
        rescue = MitigationEvidence(
            name="rescue",
            source="test",
            role="rescue",
            status="Proposal",
            requires_pq_authorization=True,
        )
        sunset = MitigationEvidence(
            name="sunset",
            source="test",
            role="sunset",
            status="Draft",
            requires_pq_authorization=True,
        )
        result = assess_bitcoin_mitigation_stack(pq, rescue, sunset)
        self.assertNotEqual(result.deployment_state, "DEPLOYABLE_MITIGATION_STACK")
        self.assertNotEqual(result.rescue_state, "RESCUE_CONSENSUS_ACTIVE")

    def test_fully_activated_stack_is_deployable(self):
        pq = MitigationEvidence(
            name="PQ auth",
            source="test",
            role="pq_authorization",
            status="Active",
            reference_implementation=True,
            security_proof_complete=True,
            test_vectors_complete=True,
            production_implementation=True,
            consensus_activated=True,
            stateless_fallback=True,
        )
        rescue = MitigationEvidence(
            name="rescue",
            source="test",
            role="rescue",
            status="Active",
            production_implementation=True,
            consensus_activated=True,
            requires_pq_authorization=True,
        )
        sunset = MitigationEvidence(
            name="sunset",
            source="test",
            role="sunset",
            status="Active",
            consensus_activated=True,
            requires_pq_authorization=True,
        )
        result = assess_bitcoin_mitigation_stack(pq, rescue, sunset)
        self.assertEqual(result.deployment_state, "DEPLOYABLE_MITIGATION_STACK")
        self.assertEqual(result.urgency, "MAINTAIN_AND_EXERCISE")


if __name__ == "__main__":
    unittest.main()

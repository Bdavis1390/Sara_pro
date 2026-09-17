import unittest

from canonical_authority_envelope import CanonicalAuthorityEnvelope, assess_canonical_authority_envelope


class CanonicalAuthorityEnvelopeTests(unittest.TestCase):
    def complete(self, **overrides):
        data = dict(
            chain="Algorand",
            adapter_class="NATIVE_REKEY",
            stable_authority_id=True,
            authenticator_versioned=True,
            authenticator_replaceable=True,
            policy_versioned=True,
            recovery_commitment_present=True,
            chain_binding_present=True,
            replay_domain_present=True,
            evidence_binding_present=True,
            explicit_human_approval_required=True,
            live_chain_support=True,
            independent_review_complete=False,
            consensus_layer_pq=False,
        )
        data.update(overrides)
        return CanonicalAuthorityEnvelope(**data)

    def test_live_adapter_requires_review_before_pilot(self):
        result = assess_canonical_authority_envelope(self.complete())
        self.assertEqual(result.migration_state, "CANONICAL_AUTHORITY_ADAPTER_REVIEW_REQUIRED")

    def test_reviewed_live_adapter_is_pilot_ready_not_auto_executable(self):
        result = assess_canonical_authority_envelope(self.complete(independent_review_complete=True))
        self.assertEqual(result.migration_state, "CANONICAL_AUTHORITY_ADAPTER_PILOT_READY")
        self.assertIn("SEPARATE_EXECUTION_APPROVAL", result.action)

    def test_roadmap_adapter_can_be_complete_but_waiting_on_chain(self):
        result = assess_canonical_authority_envelope(
            self.complete(chain="Sui", adapter_class="ADDRESS_ALIAS", live_chain_support=False)
        )
        self.assertEqual(result.migration_state, "CANONICAL_AUTHORITY_ADAPTER_WAITING_ON_CHAIN")

    def test_missing_recovery_blocks_contract(self):
        result = assess_canonical_authority_envelope(self.complete(recovery_commitment_present=False))
        self.assertEqual(result.adapter_state, "ADAPTER_CONTRACT_INCOMPLETE")

    def test_authority_envelope_does_not_claim_pq_consensus(self):
        result = assess_canonical_authority_envelope(self.complete(independent_review_complete=True))
        self.assertTrue(any("consensus" in blocker.lower() for blocker in result.blockers))


if __name__ == "__main__":
    unittest.main()

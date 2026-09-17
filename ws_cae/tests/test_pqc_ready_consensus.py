import unittest

from ws_cae.consensus_continuity import (
    ConsensusContinuityProfile,
    ConsensusEvidenceRef,
)
from ws_cae.pqc_ready_eval import PQCReadyEvidence, assess_pqc_ready
from ws_cae.reference import Profile


class PQCReadyConsensusTests(unittest.TestCase):
    def authority_profile(self):
        return Profile(
            ecosystem="ExampleChain",
            adapter_class="REPLACEABLE_AUTH",
            implementation_maturity="MAINNET",
            stable_authority_id=True,
            authenticator_replaceable=True,
            pq_authorization_state="PQ_MAINNET",
            policy_state_documented=True,
            recovery_state_documented=True,
            domain_binding_documented=True,
            evidence_state_documented=True,
            consensus_pq_state="PQ_DEPLOYED",
            protocol_commitment_state="MAINNET",
        )

    def base_evidence(self, consensus_profile=None):
        return PQCReadyEvidence(
            profile=self.authority_profile(),
            primary_evidence_documented=True,
            theoretical_security_basis_documented=True,
            implementation_efficiency_evidence=True,
            crypto_agility_documented=True,
            key_management_evaluation_documented=True,
            external_dependencies_enumerated=True,
            interoperability_evidence=True,
            consensus_profile=consensus_profile,
        )

    def consensus(self, *, key_agility="PQ_MAINNET", pq_state="PQ_DEPLOYED", validation="FULL_NODE_REEXECUTION"):
        return ConsensusContinuityProfile(
            subject_id="urn:example:chain",
            consensus_family="POS_BFT",
            mechanism_name="Example PoS+BFT",
            resource_proof="STAKE",
            finality_model="BFT_FINALITY",
            participant_auth_primitive="PQ_SIGNATURE",
            participant_key_agility=key_agility,
            local_validation_mode=validation,
            consensus_pq_state=pq_state,
            resource_proof_agility="DOCUMENTED",
            evidence=(
                ConsensusEvidenceRef(
                    "Synthetic",
                    "https://example.com/consensus",
                    "Synthetic consensus evidence for unit testing.",
                ),
            ),
        )

    def test_profile_flag_alone_cannot_reach_full_stack(self):
        result = assess_pqc_ready(self.base_evidence())
        self.assertEqual(result.evaluation_state, "AUTHORIZATION_PQC_READY_CANDIDATE")
        self.assertEqual(result.consensus_validation_state, "CONSENSUS_PROFILE_NOT_SUPPLIED")
        self.assertIn("PQ consensus claim lacks a consensus-continuity evidence profile", result.evidence_gaps)

    def test_consistent_pq_consensus_can_reach_full_stack(self):
        result = assess_pqc_ready(self.base_evidence(self.consensus()))
        self.assertTrue(result.valid)
        self.assertEqual(result.evaluation_state, "FULL_STACK_PQC_READY_CANDIDATE")
        self.assertEqual(result.self_validation_state, "SELF_VALIDATION_DOCUMENTED")

    def test_classical_validator_key_plane_blocks_full_stack(self):
        result = assess_pqc_ready(self.base_evidence(self.consensus(key_agility="ROTATABLE_CLASSICAL")))
        self.assertFalse(result.valid)
        self.assertEqual(result.evaluation_state, "AUTHORIZATION_PQC_READY_CANDIDATE")
        self.assertIn("consensus-continuity evidence does not establish full PQ consensus readiness", result.evidence_gaps)

    def test_unspecified_self_validation_blocks_full_stack(self):
        result = assess_pqc_ready(self.base_evidence(self.consensus(validation="UNSPECIFIED")))
        self.assertTrue(result.valid)
        self.assertEqual(result.evaluation_state, "AUTHORIZATION_PQC_READY_CANDIDATE")
        self.assertEqual(result.self_validation_state, "SELF_VALIDATION_NOT_ESTABLISHED")


if __name__ == "__main__":
    unittest.main()

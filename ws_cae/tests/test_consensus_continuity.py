import unittest

from ws_cae.consensus_continuity import (
    ConsensusContinuityProfile,
    ConsensusEvidenceRef,
    assess_consensus,
)


EVIDENCE = (
    ConsensusEvidenceRef(
        "Synthetic consensus evidence",
        "https://example.com/consensus",
        "Synthetic metadata used only to test classification behavior.",
    ),
)


class ConsensusContinuityTests(unittest.TestCase):
    def test_pos_bft_self_validation_is_separate_from_pq_consensus(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:pos-bft",
            consensus_family="POS_BFT",
            mechanism_name="Example BFT over PoS",
            resource_proof="STAKE",
            finality_model="BFT_FINALITY",
            participant_auth_primitive="CLASSICAL_AGGREGATABLE_SIGNATURE",
            participant_key_agility="ROTATABLE_CLASSICAL",
            local_validation_mode="FULL_NODE_REEXECUTION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="DOCUMENTED",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertTrue(result.valid)
        self.assertEqual(result.self_validation_state, "SELF_VALIDATION_DOCUMENTED")
        self.assertEqual(result.state, "CONSENSUS_CLASSICAL_OR_UNPROVEN")

    def test_proof_of_history_cannot_stand_alone_as_consensus(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:poh",
            consensus_family="OTHER_NAMED",
            mechanism_name="Proof of History",
            resource_proof="HISTORY_CLOCK",
            finality_model="UNSPECIFIED",
            participant_auth_primitive="CLASSICAL_SIGNATURE",
            participant_key_agility="ROTATABLE_CLASSICAL",
            local_validation_mode="FULL_NODE_RULE_VALIDATION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="DOCUMENTED",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertFalse(result.valid)
        self.assertIn("Proof of History alone is not a complete consensus mechanism", result.issues)

    def test_poc_capacity_requires_explicit_subtype(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:capacity",
            consensus_family="PROOF_OF_CAPACITY",
            mechanism_name="Capacity consensus",
            resource_proof="CAPACITY",
            finality_model="CHAIN_SELECTION",
            participant_auth_primitive="",
            participant_key_agility="UNKNOWN",
            local_validation_mode="FULL_NODE_RULE_VALIDATION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="DOCUMENTED",
            poc_subtype="",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertFalse(result.valid)
        self.assertIn("capacity-based PoC requires poc_subtype=PROOF_OF_CAPACITY", result.issues)

    def test_poc_coverage_requires_explicit_subtype(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:coverage",
            consensus_family="OTHER_NAMED",
            mechanism_name="Coverage mechanism",
            resource_proof="COVERAGE",
            finality_model="EXTERNAL_CHAIN_FINALITY",
            participant_auth_primitive="CLASSICAL_SIGNATURE",
            participant_key_agility="ROTATABLE_CLASSICAL",
            local_validation_mode="COMMITTEE_ATTESTATION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="RETIRED_OR_MIGRATING",
            poc_subtype="PROOF_OF_COVERAGE",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertTrue(result.valid)
        self.assertEqual(result.self_validation_state, "EXTERNAL_OR_COMMITTEE_VALIDATION_DOCUMENTED")

    def test_pq_deployed_must_match_participant_key_plane(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:inconsistent-pq",
            consensus_family="POS",
            mechanism_name="Example PoS",
            resource_proof="STAKE",
            finality_model="CHECKPOINT_FINALITY",
            participant_auth_primitive="CLASSICAL_SIGNATURE",
            participant_key_agility="ROTATABLE_CLASSICAL",
            local_validation_mode="FULL_NODE_REEXECUTION",
            consensus_pq_state="PQ_DEPLOYED",
            resource_proof_agility="DOCUMENTED",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertFalse(result.valid)
        self.assertIn("PQ_DEPLOYED requires PQ_MAINNET participant-key agility", result.issues)

    def test_space_time_tracks_resource_and_key_planes(self):
        profile = ConsensusContinuityProfile(
            subject_id="urn:example:space-time",
            consensus_family="PROOF_OF_SPACE_TIME",
            mechanism_name="Proof of Space and Time",
            resource_proof="STORAGE_SPACE",
            finality_model="CHAIN_SELECTION_WITH_TIME_PROOFS",
            participant_auth_primitive="CLASSICAL_AGGREGATABLE_SIGNATURE",
            participant_key_agility="FIXED_CLASSICAL",
            local_validation_mode="FULL_NODE_RULE_VALIDATION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="MIGRATING",
            evidence=EVIDENCE,
        )
        result = assess_consensus(profile)
        self.assertTrue(result.valid)
        self.assertEqual(result.state, "CONSENSUS_CLASSICAL_OR_UNPROVEN")


if __name__ == "__main__":
    unittest.main()

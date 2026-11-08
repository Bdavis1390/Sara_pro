import unittest

from ws_cae.consensus_continuity import (
    ConsensusContinuityProfile,
    ConsensusEvidenceRef,
    content_id,
    envelope,
)
from ws_cae.consensus_reference import consensus_dependency


class ConsensusReferenceTests(unittest.TestCase):
    def sample(self):
        return ConsensusContinuityProfile(
            subject_id="urn:example:consensus",
            consensus_family="POS_BFT",
            mechanism_name="Example PoS+BFT",
            resource_proof="STAKE",
            finality_model="BFT_FINALITY",
            participant_auth_primitive="CLASSICAL_SIGNATURE",
            participant_key_agility="ROTATABLE_CLASSICAL",
            local_validation_mode="FULL_NODE_REEXECUTION",
            consensus_pq_state="CLASSICAL_OR_UNPROVEN",
            resource_proof_agility="DOCUMENTED",
            evidence=(
                ConsensusEvidenceRef(
                    "Synthetic",
                    "https://example.com/consensus",
                    "Synthetic evidence used only for deterministic unit testing.",
                ),
            ),
        )

    def test_content_id_is_deterministic(self):
        self.assertEqual(content_id(self.sample()), content_id(self.sample()))
        self.assertTrue(content_id(self.sample()).startswith("sha256:"))

    def test_envelope_contains_consensus_assessment(self):
        result = envelope(self.sample())
        self.assertTrue(result["valid"])
        self.assertEqual(result["assessment"]["self_validation_state"], "SELF_VALIDATION_DOCUMENTED")

    def test_dependency_points_to_exact_consensus_content(self):
        dep = consensus_dependency(self.sample())
        self.assertEqual(dep.role, "CONSENSUS_CONTINUITY")
        self.assertEqual(dep.subject, content_id(self.sample()))
        self.assertTrue(dep.critical)


if __name__ == "__main__":
    unittest.main()

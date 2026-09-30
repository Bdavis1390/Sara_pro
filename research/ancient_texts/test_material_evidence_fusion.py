import unittest
from material_evidence_fusion import (
    ArtifactHypothesis,
    MaterialEvidence,
    EvidenceChannel,
    ChannelResult,
    same_manuscript_join_gate,
)
from adaptive_manuscript_sensing import (
    ArtifactState,
    SensingAction,
    recommend_next_sensing,
    SyntheticPhantom,
    algorithm_validation_state,
)

class MaterialEvidenceFusionTests(unittest.TestCase):
    def test_material_contradiction_reopens_claim(self):
        h = ArtifactHypothesis("h","fragments belong together")
        h.add(MaterialEvidence(
            "text",EvidenceChannel.TEXTUAL,ChannelResult.SUPPORTS,
            0.9,"textual-analysis","textual"
        ))
        h.add(MaterialEvidence(
            "dna",EvidenceChannel.DNA,ChannelResult.CONTRADICTS,
            0.95,"dna-study","genetic"
        ))
        self.assertEqual(
            h.claim_ceiling(),
            "HYPOTHESIS_UNDER_MATERIAL_CONFLICT",
        )

    def test_three_independent_supports_converge(self):
        h = ArtifactHypothesis("h","same production context")
        for item in [
            MaterialEvidence("t",EvidenceChannel.TEXTUAL,ChannelResult.SUPPORTS,0.8,"t","text"),
            MaterialEvidence("d",EvidenceChannel.DNA,ChannelResult.SUPPORTS,0.8,"d","dna"),
            MaterialEvidence("i",EvidenceChannel.INK_CHEMISTRY,ChannelResult.SUPPORTS,0.8,"i","chem"),
        ]:
            h.add(item)
        self.assertEqual(h.convergence_state(),"MULTICHANNEL_CONVERGENCE")

    def test_dna_contradiction_rejects_join(self):
        self.assertEqual(
            same_manuscript_join_gate(True,True,False),
            "REJECT_JOIN_MATERIAL_CONTRADICTION",
        )

    def test_xrf_is_first_step_when_lead_unknown(self):
        actions = recommend_next_sensing(ArtifactState(
            "scroll",carbonized=True,lead_detected=None,hidden_text=True
        ))
        self.assertIn(SensingAction.HANDHELD_XRF,actions)

    def test_lead_positive_adds_tomography(self):
        actions = recommend_next_sensing(ArtifactState(
            "scroll",carbonized=True,lead_detected=True,hidden_text=True
        ))
        self.assertIn(SensingAction.LAB_CT,actions)

    def test_synthetic_scroll_is_ground_truth(self):
        p = SyntheticPhantom(
            "p","HELLO","lead 1%","protocol","scan"
        )
        out = algorithm_validation_state(p,"HELLO")
        self.assertTrue(out["exact"])

if __name__ == "__main__":
    unittest.main()

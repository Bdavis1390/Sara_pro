import unittest

from agent_state_capsule import AgentStateCapsule
from causal_world_model import CausalHypothesis, CausalHypothesisSet
from general_agent_runtime import AgentAction, AgentOutcome, GeneralAgentRuntime
from adaptive_general_agent import AdaptiveGeneralAgent
from persistent_agent_store import serialize_agent_state, deserialize_agent_state
from structural_transfer import StructuralTaskSignature, propose_transfer
from regime_change import RegimeChangeDetector

class GeneralAgentV02Tests(unittest.TestCase):
    def make_model(self):
        return CausalHypothesisSet(
            hypotheses={
                "H1":CausalHypothesis("H1",{
                    "probe":{"signal":"red"},
                    "exploit":{"reward":"yes"},
                },("e1",)),
                "H2":CausalHypothesis("H2",{
                    "probe":{"signal":"blue"},
                    "exploit":{"reward":"yes"},
                },("e2",)),
            },
            probabilities={"H1":0.5,"H2":0.5},
        )

    def test_probe_has_information_when_exploit_does_not(self):
        model = self.make_model()
        self.assertGreater(
            model.expected_information_gain_bits("probe"),
            model.expected_information_gain_bits("exploit"),
        )

    def test_observation_updates_causal_belief(self):
        model = self.make_model()
        model.update("probe",{"signal":"red"})
        self.assertGreater(model.probabilities["H1"],model.probabilities["H2"])

    def test_adaptive_agent_prefers_informative_probe(self):
        runtime = GeneralAgentRuntime(
            AgentStateCapsule("s",authorization_scope=["act"])
        )
        agent = AdaptiveGeneralAgent(runtime,self.make_model())
        chosen = agent.choose_action([
            AgentAction("exploit","get reward","act",0.8,0.0,0.1,True),
            AgentAction("probe","learn rule","act",0.4,0.0,0.1,True),
        ])
        self.assertEqual(chosen.action_id,"probe")

    def test_state_round_trip_preserves_falsifiers_and_authority(self):
        state = AgentStateCapsule(
            "s",
            falsified_hypotheses=["old_rule"],
            evidence_refs=["e1"],
            authorization_scope=["read"],
        )
        runtime = GeneralAgentRuntime(state)
        blob = serialize_agent_state(state,runtime.skills,self.make_model())
        restored,skills,model = deserialize_agent_state(blob)
        self.assertEqual(restored.falsified_hypotheses,["old_rule"])
        self.assertEqual(restored.authorization_scope,["read"])
        self.assertIsNotNone(model)

    def test_structural_transfer_ignores_surface_names(self):
        a = StructuralTaskSignature(
            frozenset({"source","target"}),
            frozenset({"source_precedes_target"}),
            frozenset({"toggle_changes_target"}),
        )
        b = StructuralTaskSignature(
            frozenset({"source","target"}),
            frozenset({"source_precedes_target"}),
            frozenset({"toggle_changes_target"}),
        )
        proposal = propose_transfer("skill",a,b)
        self.assertEqual(proposal.similarity,1.0)
        self.assertEqual(
            proposal.claim_state(),
            "TRANSFER_HYPOTHESIS_REQUIRES_TARGET_VALIDATION",
        )

    def test_regime_change_requires_repeated_surprise(self):
        detector = RegimeChangeDetector(
            surprise_threshold_nats=2.0,
            consecutive_threshold=2,
        )
        self.assertFalse(detector.observe(2.5))
        self.assertTrue(detector.observe(3.0))
        self.assertEqual(detector.regime_epoch,1)

if __name__ == "__main__":
    unittest.main()

import unittest

from agent_state_capsule import AgentStateCapsule
from general_agent_runtime import (
    AgentAction,
    AgentObservation,
    AgentOutcome,
    GeneralAgentRuntime,
)
from skill_memory import SkillState
from competence_evidence import (
    BenchmarkEvidence,
    CompetenceLedger,
    EvidenceIndependence,
)
from agi_qualification_runner import InternalGateResult, run_qualification
from agi_qualification import AGIStatus

class GeneralAgentRuntimeTests(unittest.TestCase):
    def test_skill_requires_evidence(self):
        r = GeneralAgentRuntime(
            AgentStateCapsule("s", authorization_scope=["read"])
        )
        with self.assertRaises(ValueError):
            r.learn_skill(
                "x","family","desc",{"mode":"a"},{"result":"b"},
                [],[],["read"]
            )

    def test_skill_cannot_expand_authority(self):
        r = GeneralAgentRuntime(
            AgentStateCapsule("s", authorization_scope=["read"])
        )
        skill = r.learn_skill(
            "x","family","desc",{"mode":"a"},{"result":"b"},
            ["e1"],["wrong result"],["write"]
        )
        with self.assertRaises(PermissionError):
            r.apply_skill_prediction("x",{"mode":"a"},"read")

    def test_falsified_skill_prediction_is_preserved(self):
        r = GeneralAgentRuntime(
            AgentStateCapsule("s", authorization_scope=["read"])
        )
        r.learn_skill(
            "x","family","desc",{"mode":"a"},{"result":"b"},
            ["e1"],["wrong result"],["read"]
        )
        outcome = AgentOutcome("a1",True,{"result":"c"},"e2")
        r.validate_skill_from_outcome("x",outcome)
        self.assertTrue(
            any("prediction_mismatch" in x for x in r.state.falsified_hypotheses)
        )

    def test_action_ranking_prefers_safe_epistemic_value(self):
        r = GeneralAgentRuntime(
            AgentStateCapsule("s", authorization_scope=["read"])
        )
        chosen = r.choose_action([
            AgentAction("exploit","do", "read", 0.8,0.0,0.1,True),
            AgentAction("probe","learn","read",0.5,0.6,0.1,True),
        ])
        self.assertEqual(chosen.action_id,"probe")

class QualificationLedgerTests(unittest.TestCase):
    def test_provider_only_score_does_not_create_independent_breadth(self):
        ledger = CompetenceLedger()
        ledger.add(BenchmarkEvidence(
            "e","bench","1","science","science","candidate","h",
            0.99,90.0,"skilled adults",
            EvidenceIndependence.PROVIDER_INTERNAL,
            False,False,False,"LOW","source"
        ))
        self.assertEqual(
            ledger.family_coverage("candidate",{"science"}),
            0.0,
        )

    def test_broad_external_gate_still_requires_internal_runtime(self):
        ledger = CompetenceLedger()
        families = {"science"}
        ledger.add(BenchmarkEvidence(
            "e1","b","1","science","science","candidate","h",
            0.8,60.0,"skilled adults",
            EvidenceIndependence.INDEPENDENT_BLIND,
            True,True,True,"LOW","source"
        ))
        internal = InternalGateResult(
            metacognition=False,
            identifiability_awareness=True,
            epistemic_action=True,
            causal_world_model=True,
            cross_domain_transfer=True,
            online_adaptation=True,
            calibration=True,
            governed_autonomy=True,
            state_continuity=True,
            representation_shift=True,
        )
        report = run_qualification(
            ledger,"candidate",internal,families,project_most_threshold=0.6
        )
        self.assertEqual(report.status, AGIStatus.AGI_CANDIDATE_NOT_CERTIFIED)
        self.assertTrue(any("metacognition" in x for x in report.missing))

if __name__ == "__main__":
    unittest.main()

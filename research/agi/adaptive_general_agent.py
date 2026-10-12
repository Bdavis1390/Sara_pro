from __future__ import annotations
from dataclasses import dataclass, field

from agent_state_capsule import AgentStateCapsule
from causal_world_model import CausalHypothesisSet
from general_agent_runtime import AgentAction, AgentOutcome, GeneralAgentRuntime
from regime_change import RegimeChangeDetector
from structural_transfer import (
    StructuralTaskSignature,
    TransferProposal,
    propose_transfer,
)

@dataclass
class AdaptiveGeneralAgent:
    runtime: GeneralAgentRuntime
    world_model: CausalHypothesisSet
    regime_detector: RegimeChangeDetector = field(default_factory=RegimeChangeDetector)

    def choose_action(self, actions: list[AgentAction]) -> AgentAction:
        enriched = []
        for action in actions:
            eig = self.world_model.expected_information_gain_bits(action.action_id)
            enriched.append(AgentAction(
                action_id=action.action_id,
                description=action.description,
                authorization_scope=action.authorization_scope,
                task_value=action.task_value,
                epistemic_value=max(action.epistemic_value,eig),
                risk=action.risk,
                reversible=action.reversible,
            ))
        return self.runtime.choose_action(enriched)

    def learn_from_outcome(self, outcome: AgentOutcome) -> dict:
        surprise = self.world_model.surprise_nats(
            outcome.action_id,
            outcome.observed_effects,
        )
        regime_changed = self.regime_detector.observe(surprise)
        self.world_model.update(
            outcome.action_id,
            outcome.observed_effects,
        )
        self.runtime.record_outcome(outcome)

        if regime_changed:
            self.runtime.state.falsified_hypotheses.append(
                f"regime_change_epoch:{self.regime_detector.regime_epoch}:"
                f"{outcome.evidence_ref}"
            )
            self.runtime.state.epistemic_gaps.append(
                "Previously predictive causal model may no longer describe current regime."
            )

        best_id,best_p = self.world_model.best_hypothesis()
        self.runtime.state.beliefs = dict(self.world_model.probabilities)
        return {
            "surprise_nats":surprise,
            "regime_changed":regime_changed,
            "best_hypothesis":best_id,
            "best_probability":best_p,
        }

    def transfer_skill(
        self,
        skill_id: str,
        source_signature: StructuralTaskSignature,
        target_signature: StructuralTaskSignature,
    ) -> TransferProposal:
        if skill_id not in self.runtime.skills.skills:
            raise KeyError(skill_id)
        return propose_transfer(
            skill_id,
            source_signature,
            target_signature,
        )

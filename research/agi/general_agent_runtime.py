from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable

from agent_state_capsule import AgentStateCapsule
from skill_memory import Skill, SkillLibrary

@dataclass(frozen=True)
class AgentObservation:
    observation_id: str
    state_features: dict[str, str]
    evidence_ref: str

@dataclass(frozen=True)
class AgentAction:
    action_id: str
    description: str
    authorization_scope: str
    task_value: float
    epistemic_value: float
    risk: float
    reversible: bool = True

@dataclass(frozen=True)
class AgentOutcome:
    action_id: str
    success: bool
    observed_effects: dict[str, str]
    evidence_ref: str

@dataclass
class GeneralAgentRuntime:
    state: AgentStateCapsule
    skills: SkillLibrary = field(default_factory=SkillLibrary)
    observations: list[AgentObservation] = field(default_factory=list)
    outcomes: list[AgentOutcome] = field(default_factory=list)

    def observe(self, observation: AgentObservation) -> None:
        self.observations.append(observation)
        self.state.observations.append(observation.observation_id)
        self.state.evidence_refs.append(observation.evidence_ref)

    def choose_action(self, actions: list[AgentAction]) -> AgentAction:
        eligible = [
            a for a in actions
            if a.authorization_scope in self.state.authorization_scope
        ]
        if not eligible:
            raise PermissionError("no authorized actions")
        def utility(a: AgentAction) -> float:
            irreversibility_penalty = 0.5 if not a.reversible else 0.0
            return (
                a.task_value
                + a.epistemic_value
                - a.risk
                - irreversibility_penalty
            )
        return max(eligible, key=utility)

    def record_outcome(self, outcome: AgentOutcome) -> None:
        self.outcomes.append(outcome)
        self.state.action_outcomes.append(outcome.action_id)
        self.state.evidence_refs.append(outcome.evidence_ref)

    def learn_skill(
        self,
        skill_id: str,
        task_family: str,
        description: str,
        preconditions: dict[str, str],
        expected_effects: dict[str, str],
        evidence_refs: list[str],
        falsifiers: list[str],
        authorized_scopes: list[str],
    ) -> Skill:
        skill = Skill(
            skill_id=skill_id,
            task_family=task_family,
            description=description,
            preconditions=preconditions,
            expected_effects=expected_effects,
            confidence=0.5,
            evidence_refs=evidence_refs,
            falsifiers=falsifiers,
            authorized_scopes=authorized_scopes,
        )
        self.skills.add(skill)
        return skill

    def apply_skill_prediction(
        self,
        skill_id: str,
        context: dict[str, str],
        authorization_scope: str,
    ) -> dict[str, str]:
        skill = self.skills.skills[skill_id]
        state = skill.applicability(context, authorization_scope)
        if state != "APPLICABLE":
            raise PermissionError(state)
        return dict(skill.expected_effects)

    def validate_skill_from_outcome(
        self,
        skill_id: str,
        outcome: AgentOutcome,
    ) -> None:
        skill = self.skills.skills[skill_id]
        predicted = skill.expected_effects
        matched = all(
            outcome.observed_effects.get(k) == v
            for k, v in predicted.items()
        )
        skill.record_outcome(matched and outcome.success, outcome.evidence_ref)
        if not matched:
            self.state.falsified_hypotheses.append(
                f"skill:{skill_id}:prediction_mismatch:{outcome.evidence_ref}"
            )

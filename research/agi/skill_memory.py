from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json

class SkillState(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    VALIDATED = "VALIDATED"
    DEGRADED = "DEGRADED"
    RETIRED = "RETIRED"

@dataclass
class Skill:
    skill_id: str
    task_family: str
    description: str
    preconditions: dict[str, str]
    expected_effects: dict[str, str]
    confidence: float
    evidence_refs: list[str] = field(default_factory=list)
    falsifiers: list[str] = field(default_factory=list)
    authorized_scopes: list[str] = field(default_factory=list)
    state: SkillState = SkillState.HYPOTHESIS
    successes: int = 0
    failures: int = 0

    def validate(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0,1]")
        if not self.task_family:
            raise ValueError("task_family required")
        if not self.evidence_refs:
            raise ValueError("learned skill requires evidence lineage")

    def fingerprint(self) -> str:
        self.validate()
        payload = json.dumps({
            "task_family": self.task_family,
            "description": self.description,
            "preconditions": self.preconditions,
            "expected_effects": self.expected_effects,
            "evidence_refs": sorted(self.evidence_refs),
            "falsifiers": sorted(self.falsifiers),
        }, sort_keys=True)
        return sha256(payload.encode()).hexdigest()

    def applicability(self, context: dict[str, str], authorization_scope: str) -> str:
        self.validate()
        if self.state == SkillState.RETIRED:
            return "RETIRED"
        if authorization_scope not in self.authorized_scopes:
            return "BLOCK_UNAUTHORIZED_SCOPE"
        for key, value in self.preconditions.items():
            if context.get(key) != value:
                return "OUT_OF_SCOPE"
        if self.state == SkillState.DEGRADED:
            return "REQUIRES_REVALIDATION"
        return "APPLICABLE"

    def record_outcome(self, success: bool, evidence_ref: str) -> None:
        self.evidence_refs.append(evidence_ref)
        if success:
            self.successes += 1
        else:
            self.failures += 1

        total = self.successes + self.failures
        # Beta(1,1) posterior mean over Bernoulli success as a simple,
        # explicit reliability estimate; not a universal skill metric.
        self.confidence = (self.successes + 1) / (total + 2)

        if self.failures >= 2 and self.confidence < 0.5:
            self.state = SkillState.DEGRADED
        if self.failures >= 4 and self.confidence < 0.35:
            self.state = SkillState.RETIRED
        if self.successes >= 3 and self.confidence >= 0.7 and self.failures == 0:
            self.state = SkillState.VALIDATED

@dataclass
class SkillLibrary:
    skills: dict[str, Skill] = field(default_factory=dict)

    def add(self, skill: Skill) -> None:
        skill.validate()
        if skill.skill_id in self.skills:
            raise ValueError("duplicate skill")
        self.skills[skill.skill_id] = skill

    def candidates(
        self,
        task_family: str,
        context: dict[str, str],
        authorization_scope: str,
    ) -> list[Skill]:
        out = []
        for skill in self.skills.values():
            if skill.task_family != task_family:
                continue
            if skill.applicability(context, authorization_scope) == "APPLICABLE":
                out.append(skill)
        return sorted(out, key=lambda s: s.confidence, reverse=True)

    def transfer_candidates(
        self,
        structural_features: set[str],
        authorization_scope: str,
    ) -> list[Skill]:
        # Transfer is conservative: feature overlap only proposes a candidate;
        # it does not bypass precondition checking or authorize execution.
        scored = []
        for skill in self.skills.values():
            if authorization_scope not in skill.authorized_scopes:
                continue
            feature_keys = set(skill.preconditions)
            union = feature_keys | structural_features
            overlap = len(feature_keys & structural_features) / len(union) if union else 0.0
            if overlap > 0:
                scored.append((overlap, skill))
        return [skill for _, skill in sorted(scored, key=lambda x: x[0], reverse=True)]

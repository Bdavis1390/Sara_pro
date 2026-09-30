from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
import json

@dataclass
class AgentStateCapsule:
    session_id: str
    goals: list[str] = field(default_factory=list)
    beliefs: dict[str, float] = field(default_factory=dict)
    causal_rules: list[str] = field(default_factory=list)
    falsified_hypotheses: list[str] = field(default_factory=list)
    unresolved_hypotheses: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    action_outcomes: list[str] = field(default_factory=list)
    epistemic_gaps: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    authorization_scope: list[str] = field(default_factory=list)

    def validate(self) -> None:
        for name, p in self.beliefs.items():
            if not 0 <= p <= 1:
                raise ValueError(f"belief {name} must be in [0,1]")

    def fingerprint(self) -> str:
        self.validate()
        payload = json.dumps(
            {
                "session_id": self.session_id,
                "goals": self.goals,
                "beliefs": self.beliefs,
                "causal_rules": self.causal_rules,
                "falsified_hypotheses": self.falsified_hypotheses,
                "unresolved_hypotheses": self.unresolved_hypotheses,
                "observations": self.observations,
                "action_outcomes": self.action_outcomes,
                "epistemic_gaps": self.epistemic_gaps,
                "evidence_refs": self.evidence_refs,
                "authorization_scope": self.authorization_scope,
            },
            sort_keys=True,
        )
        return sha256(payload.encode()).hexdigest()

    def compact(self) -> dict:
        # Preserve decision-relevant state, not verbatim hidden reasoning.
        self.validate()
        return {
            "session_id": self.session_id,
            "goals": self.goals[-8:],
            "beliefs": dict(sorted(
                self.beliefs.items(),
                key=lambda kv: abs(kv[1] - 0.5),
                reverse=True,
            )[:32]),
            "causal_rules": self.causal_rules[-32:],
            "falsified_hypotheses": self.falsified_hypotheses[-32:],
            "unresolved_hypotheses": self.unresolved_hypotheses[-32:],
            "observations": self.observations[-64:],
            "action_outcomes": self.action_outcomes[-64:],
            "epistemic_gaps": self.epistemic_gaps[-32:],
            "evidence_refs": self.evidence_refs[-64:],
            "authorization_scope": self.authorization_scope,
            "fingerprint": self.fingerprint(),
        }

def state_continuity_invariants(before: AgentStateCapsule, after: AgentStateCapsule) -> list[str]:
    violations: list[str] = []
    if not set(before.authorization_scope).issubset(set(after.authorization_scope)):
        # Losing authorization context is unsafe; gaining scope is checked elsewhere.
        violations.append("authorization context lost")
    if not set(before.falsified_hypotheses).issubset(set(after.falsified_hypotheses)):
        violations.append("falsified hypotheses forgotten")
    if not set(before.evidence_refs).issubset(set(after.evidence_refs)):
        violations.append("evidence lineage lost")
    return violations

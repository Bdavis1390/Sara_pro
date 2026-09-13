"""Relying-party policy evaluation for WS-CAE profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .reference import CONSENSUS_STATES, MATURITY_ORDER, PQ_AUTH_STATES, Assessment, Profile


@dataclass(frozen=True)
class Policy:
    name: str
    minimum_maturity: str = "ROADMAP"
    accepted_pq_authorization_states: tuple[str, ...] = tuple(sorted(PQ_AUTH_STATES))
    accepted_consensus_states: tuple[str, ...] = tuple(sorted(CONSENSUS_STATES))
    require_stable_authority_id: bool = False
    require_authenticator_replaceable: bool = False
    require_policy_state_documented: bool = False
    require_recovery_state_documented: bool = False
    require_domain_binding_documented: bool = True
    require_evidence_state_documented: bool = True


@dataclass(frozen=True)
class PolicyAssessment:
    policy_name: str
    passed: bool
    failures: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(profile: Profile, reference: Assessment, policy: Policy) -> PolicyAssessment:
    failures: list[str] = []
    if not policy.name.strip():
        failures.append("policy name must be non-empty")
    if policy.minimum_maturity not in MATURITY_ORDER:
        failures.append("minimum_maturity is not recognized")
    if not policy.accepted_pq_authorization_states or any(x not in PQ_AUTH_STATES for x in policy.accepted_pq_authorization_states):
        failures.append("accepted_pq_authorization_states is invalid")
    if not policy.accepted_consensus_states or any(x not in CONSENSUS_STATES for x in policy.accepted_consensus_states):
        failures.append("accepted_consensus_states is invalid")
    if not reference.valid:
        failures.append("reference profile is nonconformant")

    if profile.implementation_maturity in MATURITY_ORDER and policy.minimum_maturity in MATURITY_ORDER:
        if MATURITY_ORDER[profile.implementation_maturity] < MATURITY_ORDER[policy.minimum_maturity]:
            failures.append(f"maturity {profile.implementation_maturity} is below required {policy.minimum_maturity}")
    if profile.pq_authorization_state not in policy.accepted_pq_authorization_states:
        failures.append(f"PQ authorization state {profile.pq_authorization_state} is outside policy")
    if profile.consensus_pq_state not in policy.accepted_consensus_states:
        failures.append(f"consensus state {profile.consensus_pq_state} is outside policy")

    checks = (
        (policy.require_stable_authority_id, profile.stable_authority_id, "stable authority identity"),
        (policy.require_authenticator_replaceable, profile.authenticator_replaceable, "replaceable authenticator"),
        (policy.require_policy_state_documented, profile.policy_state_documented, "documented policy"),
        (policy.require_recovery_state_documented, profile.recovery_state_documented, "documented recovery"),
        (policy.require_domain_binding_documented, profile.domain_binding_documented, "domain/replay binding"),
        (policy.require_evidence_state_documented, profile.evidence_state_documented, "evidence state"),
    )
    for required, present, label in checks:
        if required and not present:
            failures.append(f"policy requires {label}")

    return PolicyAssessment(policy.name, not failures, tuple(failures))

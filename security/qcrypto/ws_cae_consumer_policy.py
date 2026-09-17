"""Consumer-side policy evaluation for WS-CAE authority profiles.

Read-only defensive tooling. This module lets custodians, exchanges, wallets,
auditors, treasuries, or other relying parties express minimum authority-state
requirements independently of a chain's implementation details. It performs no
signing, key generation, wallet access, transaction construction, broadcast, or
asset movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ws_cae_reference_conformance import (
    CONSENSUS_STATES,
    MATURITY_ORDER,
    PQ_AUTH_STATES,
    WSCAEReferenceAssessment,
    WSCAEReferenceProfile,
)


@dataclass(frozen=True)
class WSCAEConsumerPolicy:
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
class WSCAEPolicyAssessment:
    policy_name: str
    passed: bool
    failures: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_policy(policy: WSCAEConsumerPolicy) -> tuple[str, ...]:
    issues: list[str] = []
    if not policy.name.strip():
        issues.append("policy name must be non-empty")
    if policy.minimum_maturity not in MATURITY_ORDER:
        issues.append("minimum_maturity must be ROADMAP, DRAFT, DEVNET, TESTNET, or MAINNET")
    if not policy.accepted_pq_authorization_states:
        issues.append("accepted_pq_authorization_states must not be empty")
    elif any(item not in PQ_AUTH_STATES for item in policy.accepted_pq_authorization_states):
        issues.append("accepted_pq_authorization_states contains an unrecognized state")
    if not policy.accepted_consensus_states:
        issues.append("accepted_consensus_states must not be empty")
    elif any(item not in CONSENSUS_STATES for item in policy.accepted_consensus_states):
        issues.append("accepted_consensus_states contains an unrecognized state")
    return tuple(issues)


def assess_consumer_policy(
    profile: WSCAEReferenceProfile,
    reference: WSCAEReferenceAssessment,
    policy: WSCAEConsumerPolicy,
) -> WSCAEPolicyAssessment:
    failures: list[str] = list(validate_policy(policy))

    if not reference.valid:
        failures.append("reference profile is nonconformant")

    if profile.implementation_maturity in MATURITY_ORDER and policy.minimum_maturity in MATURITY_ORDER:
        if MATURITY_ORDER[profile.implementation_maturity] < MATURITY_ORDER[policy.minimum_maturity]:
            failures.append(
                f"implementation maturity {profile.implementation_maturity} is below required {policy.minimum_maturity}"
            )

    if profile.pq_authorization_state not in policy.accepted_pq_authorization_states:
        failures.append(
            f"PQ authorization state {profile.pq_authorization_state} is outside policy"
        )

    if profile.consensus_pq_state not in policy.accepted_consensus_states:
        failures.append(
            f"consensus state {profile.consensus_pq_state} is outside policy"
        )

    required_flags = (
        (policy.require_stable_authority_id, profile.stable_authority_id, "stable authority identity"),
        (policy.require_authenticator_replaceable, profile.authenticator_replaceable, "replaceable authenticator"),
        (policy.require_policy_state_documented, profile.policy_state_documented, "documented authorization policy"),
        (policy.require_recovery_state_documented, profile.recovery_state_documented, "documented recovery state"),
        (policy.require_domain_binding_documented, profile.domain_binding_documented, "documented domain/replay binding"),
        (policy.require_evidence_state_documented, profile.evidence_state_documented, "documented evidence state"),
    )
    for required, present, label in required_flags:
        if required and not present:
            failures.append(f"policy requires {label}")

    return WSCAEPolicyAssessment(
        policy_name=policy.name,
        passed=not failures,
        failures=tuple(failures),
    )

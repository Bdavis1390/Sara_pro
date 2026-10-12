"""Executable WS-CAE reference-profile conformance checks.

This module classifies documented authority-state maturity only. It performs no
signing, key generation, transaction construction, or asset movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


MATURITY_ORDER = {
    "ROADMAP": 0,
    "DRAFT": 1,
    "DEVNET": 2,
    "TESTNET": 3,
    "MAINNET": 4,
}

PQ_AUTH_STATES = {
    "NONE",
    "PLUGGABLE_AUTH_ONLY",
    "PQ_NON_MAINNET",
    "PQ_MAINNET",
}

CONSENSUS_STATES = {
    "CLASSICAL_OR_UNPROVEN",
    "PQ_RESEARCH_OR_PARTIAL",
    "PQ_DEPLOYED",
}


@dataclass(frozen=True)
class WSCAEReferenceProfile:
    ecosystem: str
    adapter_class: str
    implementation_maturity: str
    stable_authority_id: bool
    authenticator_replaceable: bool
    pq_authorization_state: str
    policy_state_documented: bool
    recovery_state_documented: bool
    domain_binding_documented: bool
    evidence_state_documented: bool
    consensus_pq_state: str = "CLASSICAL_OR_UNPROVEN"


@dataclass(frozen=True)
class WSCAEReferenceAssessment:
    valid: bool
    authority_state: str
    maturity_state: str
    pq_authorization_state: str
    consensus_boundary: str
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_reference_profile(profile: WSCAEReferenceProfile) -> WSCAEReferenceAssessment:
    issues: list[str] = []

    if profile.implementation_maturity not in MATURITY_ORDER:
        issues.append("implementation_maturity must be ROADMAP, DRAFT, DEVNET, TESTNET, or MAINNET")

    if profile.pq_authorization_state not in PQ_AUTH_STATES:
        issues.append("pq_authorization_state is not recognized")

    if profile.consensus_pq_state not in CONSENSUS_STATES:
        issues.append("consensus_pq_state is not recognized")

    if profile.stable_authority_id and profile.authenticator_replaceable:
        authority_state = "AUTHORITY_ABSTRACTION_PRESENT"
    elif profile.authenticator_replaceable:
        authority_state = "AUTHENTICATOR_AGILITY_WITHOUT_STABLE_AUTHORITY_EVIDENCE"
    else:
        authority_state = "AUTHORITY_ABSTRACTION_NOT_ESTABLISHED"

    if profile.implementation_maturity in MATURITY_ORDER:
        maturity_state = f"IMPLEMENTATION_{profile.implementation_maturity}"
    else:
        maturity_state = "IMPLEMENTATION_STATE_INVALID"

    if not profile.domain_binding_documented:
        issues.append("domain/replay binding is not documented")
    if not profile.evidence_state_documented:
        issues.append("evidence state is not documented")

    if profile.consensus_pq_state == "PQ_DEPLOYED":
        consensus_boundary = "CONSENSUS_PQ_DEPLOYED"
    else:
        consensus_boundary = "ACCOUNT_AUTHORITY_RESULT_DOES_NOT_ESTABLISH_PQ_CONSENSUS"

    return WSCAEReferenceAssessment(
        valid=not issues,
        authority_state=authority_state,
        maturity_state=maturity_state,
        pq_authorization_state=profile.pq_authorization_state,
        consensus_boundary=consensus_boundary,
        issues=tuple(issues),
    )

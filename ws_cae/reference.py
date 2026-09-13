"""WS-CAE reference authority-state classifier."""

from __future__ import annotations

from dataclasses import asdict, dataclass

MATURITY_ORDER = {"ROADMAP": 0, "DRAFT": 1, "DEVNET": 2, "TESTNET": 3, "MAINNET": 4}
PQ_AUTH_STATES = {"NONE", "PLUGGABLE_AUTH_ONLY", "PQ_NON_MAINNET", "PQ_MAINNET_LIMITED", "PQ_MAINNET"}
CONSENSUS_STATES = {"CLASSICAL_OR_UNPROVEN", "PQ_RESEARCH_OR_PARTIAL", "PQ_DEPLOYED"}
PROTOCOL_COMMITMENT_STATES = {"UNSPECIFIED", "RESEARCH", "GOVERNANCE_SELECTED", "FORK_SCHEDULED", "MAINNET"}


@dataclass(frozen=True)
class Profile:
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
    protocol_commitment_state: str = "UNSPECIFIED"


@dataclass(frozen=True)
class Assessment:
    valid: bool
    authority_state: str
    maturity_state: str
    pq_authorization_state: str
    protocol_commitment_state: str
    consensus_boundary: str
    issues: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess(profile: Profile) -> Assessment:
    issues: list[str] = []
    if profile.implementation_maturity not in MATURITY_ORDER:
        issues.append("implementation_maturity is not recognized")
    if profile.pq_authorization_state not in PQ_AUTH_STATES:
        issues.append("pq_authorization_state is not recognized")
    if profile.consensus_pq_state not in CONSENSUS_STATES:
        issues.append("consensus_pq_state is not recognized")
    if profile.protocol_commitment_state not in PROTOCOL_COMMITMENT_STATES:
        issues.append("protocol_commitment_state is not recognized")

    if profile.stable_authority_id and profile.authenticator_replaceable:
        authority = "AUTHORITY_ABSTRACTION_PRESENT"
    elif profile.authenticator_replaceable:
        authority = "AUTHENTICATOR_AGILITY_WITHOUT_STABLE_AUTHORITY_EVIDENCE"
    else:
        authority = "AUTHORITY_ABSTRACTION_NOT_ESTABLISHED"

    maturity = (
        f"IMPLEMENTATION_{profile.implementation_maturity}"
        if profile.implementation_maturity in MATURITY_ORDER
        else "IMPLEMENTATION_STATE_INVALID"
    )
    if not profile.domain_binding_documented:
        issues.append("domain/replay binding is not documented")
    if not profile.evidence_state_documented:
        issues.append("evidence state is not documented")

    consensus = (
        "CONSENSUS_PQ_DEPLOYED"
        if profile.consensus_pq_state == "PQ_DEPLOYED"
        else "ACCOUNT_AUTHORITY_RESULT_DOES_NOT_ESTABLISH_PQ_CONSENSUS"
    )
    return Assessment(
        not issues,
        authority,
        maturity,
        profile.pq_authorization_state,
        profile.protocol_commitment_state,
        consensus,
        tuple(issues),
    )

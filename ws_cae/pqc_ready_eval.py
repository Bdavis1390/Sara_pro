"""Neutral, read-only PQC-ready evaluation profile for blockchain migration.

This module does not score winners or choose cryptographic algorithms. It
normalizes evidence so an external evaluation process can apply its own
weights, thresholds, and policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .reference import Profile, assess as assess_profile


@dataclass(frozen=True)
class PQCReadyEvidence:
    profile: Profile
    primary_evidence_documented: bool
    theoretical_security_basis_documented: bool
    implementation_efficiency_evidence: bool
    crypto_agility_documented: bool
    key_management_evaluation_documented: bool
    external_dependencies_enumerated: bool
    interoperability_evidence: bool


@dataclass(frozen=True)
class PQCReadyAssessment:
    valid: bool
    evaluation_state: str
    authorization_state: str
    consensus_state: str
    implementation_state: str
    protocol_commitment_state: str
    evidence_gaps: tuple[str, ...]
    implementation_evidence_complete: bool

    def to_dict(self) -> dict:
        return asdict(self)


def assess_pqc_ready(evidence: PQCReadyEvidence) -> PQCReadyAssessment:
    profile_result = assess_profile(evidence.profile)
    gaps: list[str] = list(profile_result.issues)

    checks = {
        "primary evidence is not documented": evidence.primary_evidence_documented,
        "theoretical security basis is not documented": evidence.theoretical_security_basis_documented,
        "implementation-efficiency evidence is not documented": evidence.implementation_efficiency_evidence,
        "crypto-agility behavior is not documented": evidence.crypto_agility_documented,
        "key-management evaluation is not documented": evidence.key_management_evaluation_documented,
        "external critical dependencies are not enumerated": evidence.external_dependencies_enumerated,
        "interoperability evidence is not documented": evidence.interoperability_evidence,
    }
    for message, passed in checks.items():
        if not passed:
            gaps.append(message)

    profile = evidence.profile
    authorization_mainnet = profile.pq_authorization_state == "PQ_MAINNET"
    authorization_limited = profile.pq_authorization_state == "PQ_MAINNET_LIMITED"
    consensus_mainnet = profile.consensus_pq_state == "PQ_DEPLOYED"
    implementation_mainnet = profile.implementation_maturity == "MAINNET"

    if authorization_mainnet and consensus_mainnet and implementation_mainnet and not gaps:
        state = "FULL_STACK_PQC_READY_CANDIDATE"
    elif authorization_mainnet and implementation_mainnet:
        state = "AUTHORIZATION_PQC_READY_CANDIDATE"
    elif authorization_limited and implementation_mainnet:
        state = "LIMITED_MAINNET_PQ_PATH"
    elif profile.authenticator_replaceable or profile.pq_authorization_state in {
        "PLUGGABLE_AUTH_ONLY",
        "PQ_NON_MAINNET",
    }:
        state = "MIGRATION_FOUNDATION_PRESENT"
    else:
        state = "PQC_MIGRATION_FOUNDATION_NOT_ESTABLISHED"

    if not authorization_mainnet:
        gaps.append("general mainnet PQ authorization is not established")
    if not consensus_mainnet:
        gaps.append("PQ consensus deployment is not established")
    if not implementation_mainnet:
        gaps.append("implementation is not mainnet")
    if not profile.recovery_state_documented:
        gaps.append("recovery state is not documented")

    # Preserve deterministic order while removing duplicates.
    unique_gaps = tuple(dict.fromkeys(gaps))
    evidence_complete = all(checks.values())

    return PQCReadyAssessment(
        valid=profile_result.valid and evidence.primary_evidence_documented,
        evaluation_state=state,
        authorization_state=profile.pq_authorization_state,
        consensus_state=profile.consensus_pq_state,
        implementation_state=profile.implementation_maturity,
        protocol_commitment_state=profile.protocol_commitment_state,
        evidence_gaps=unique_gaps,
        implementation_evidence_complete=evidence_complete,
    )

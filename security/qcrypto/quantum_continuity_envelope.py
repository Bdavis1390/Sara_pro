"""Defensive readiness model for a Quantum Continuity Envelope (QCE).

QCE virtualizes authorization so custody policy, account identity, recovery, and
signature algorithms can evolve independently. This module does not implement
cryptographic signing, secret sharing, wallet access, key recovery, or live-chain
interaction.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ContinuityEnvelopeEvidence:
    name: str
    source: str
    programmable_enforcement_layer: bool = False
    stable_authority_identifier: bool = False
    replaceable_authenticator: bool = False
    signature_agnostic_threshold_gate: bool = False
    pq_member_authentication_available: bool = False
    independent_pq_families_available: bool = False
    precommitted_recovery_path: bool = False
    stateful_signing_present: bool = False
    state_reuse_controls_verified: bool = False
    independent_review_complete: bool = False
    chain_native_pq_consensus: bool = False


@dataclass(frozen=True)
class ContinuityEnvelopeAssessment:
    authorization_state: str
    algorithm_state: str
    recovery_state: str
    operational_state: str
    migration_action: str
    residual_risks: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_continuity_envelope(evidence: ContinuityEnvelopeEvidence) -> ContinuityEnvelopeAssessment:
    """Assess whether a crypto-agile PQ authorization envelope is defensibly usable."""

    residual: list[str] = []

    auth_virtualized = all(
        (
            evidence.programmable_enforcement_layer,
            evidence.stable_authority_identifier,
            evidence.replaceable_authenticator,
            evidence.signature_agnostic_threshold_gate,
        )
    )

    if auth_virtualized:
        authorization_state = "AUTHORIZATION_VIRTUALIZED"
    elif evidence.programmable_enforcement_layer and evidence.replaceable_authenticator:
        authorization_state = "CRYPTO_AGILE_AUTH_SUBSTRATE"
    else:
        authorization_state = "AUTHORIZATION_COUPLED_TO_LEGACY_PATH"

    if evidence.pq_member_authentication_available and evidence.independent_pq_families_available:
        algorithm_state = "ALGORITHM_DIVERSE_PQ_AUTH_AVAILABLE"
    elif evidence.pq_member_authentication_available:
        algorithm_state = "SINGLE_FAMILY_PQ_AUTH_AVAILABLE"
        residual.append("A single post-quantum signature family leaves an avoidable cryptographic monoculture risk.")
    else:
        algorithm_state = "PQ_AUTHENTICATOR_NOT_YET_AVAILABLE"
        residual.append("Post-quantum member authentication is not yet available in this evidence record.")

    if evidence.precommitted_recovery_path:
        recovery_state = "PRECOMMITTED_RECOVERY_AVAILABLE"
    else:
        recovery_state = "RECOVERY_NOT_PREPOSITIONED"
        residual.append("A recovery authority or commitment is not prepositioned before classical-key failure.")

    if evidence.stateful_signing_present and not evidence.state_reuse_controls_verified:
        operational_state = "BLOCKED_STATE_REUSE_RISK"
        residual.append("Stateful signing is present without verified single-use / crash-safe state-consumption controls.")
    elif auth_virtualized and algorithm_state == "ALGORITHM_DIVERSE_PQ_AUTH_AVAILABLE" and evidence.precommitted_recovery_path:
        operational_state = (
            "QCE_PILOT_READY" if evidence.independent_review_complete else "QCE_INTEGRATION_CANDIDATE_REVIEW_REQUIRED"
        )
    elif authorization_state == "CRYPTO_AGILE_AUTH_SUBSTRATE":
        operational_state = "QCE_SUBSTRATE_READY_PQ_INTEGRATION_PENDING"
    else:
        operational_state = "QCE_DESIGN_OR_EARLY_INTEGRATION"

    if not evidence.chain_native_pq_consensus:
        residual.append("Base-layer consensus or validator authentication remains outside the QCE protection boundary.")
    if not evidence.independent_review_complete:
        residual.append("Independent review of the complete deployed authorization and recovery path is incomplete or not established.")

    if operational_state == "QCE_PILOT_READY":
        action = "PILOT_HIGH_VALUE_AUTHORITY_DOMAINS_WITH_BOUNDED_CAPS_AND_RECOVERY_DRILLS"
    elif operational_state == "QCE_INTEGRATION_CANDIDATE_REVIEW_REQUIRED":
        action = "INDEPENDENTLY_REVIEW_THEN_PILOT_WITH_BOUNDED_VALUE"
    elif operational_state == "BLOCKED_STATE_REUSE_RISK":
        action = "FIX_STATE_CONSUMPTION_AND_RETRY_SAFETY_BEFORE_DEPLOYMENT"
    elif operational_state == "QCE_SUBSTRATE_READY_PQ_INTEGRATION_PENDING":
        action = "ADD_PQ_AUTHENTICATORS_AND_PRECOMMITTED_RECOVERY"
    else:
        action = "BUILD_PROGRAMMABLE_AUTHORIZATION_AND_RECOVERY_SUBSTRATE"

    return ContinuityEnvelopeAssessment(
        authorization_state=authorization_state,
        algorithm_state=algorithm_state,
        recovery_state=recovery_state,
        operational_state=operational_state,
        migration_action=action,
        residual_risks=tuple(residual),
    )

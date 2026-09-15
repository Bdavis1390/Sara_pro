"""Defensive Bitcoin post-quantum mitigation readiness classifier.

This module tracks protocol maturity and dependencies only. It does not sign
transactions, access wallets, recover keys, or interact with live networks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MitigationEvidence:
    name: str
    source: str
    role: str
    status: str
    reference_implementation: bool = False
    security_proof_complete: bool = False
    test_vectors_complete: bool = False
    production_implementation: bool = False
    consensus_activated: bool = False
    requires_pq_authorization: bool = False
    stateful_primary: bool = False
    stateless_fallback: bool = False


@dataclass(frozen=True)
class MitigationReadiness:
    pq_authorization_state: str
    rescue_state: str
    sunset_state: str
    deployment_state: str
    urgency: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_bitcoin_mitigation_stack(
    pq_authorization: MitigationEvidence,
    rescue: MitigationEvidence,
    sunset: MitigationEvidence,
) -> MitigationReadiness:
    """Assess whether public Bitcoin PQ proposals form a deployable stack.

    Draft specifications, reference implementations, production code, and
    consensus activation are separate maturity levels. Rescue and legacy-sunset
    designs that depend on PQ authorization remain blocked until a suitable PQ
    authorization/output mechanism is active.
    """

    gaps: list[str] = []

    if pq_authorization.consensus_activated:
        pq_state = "PQ_AUTHORIZATION_CONSENSUS_ACTIVE"
    elif pq_authorization.production_implementation:
        pq_state = "PQ_AUTHORIZATION_PRODUCTION_IMPLEMENTED_NOT_ACTIVATED"
    elif pq_authorization.reference_implementation:
        pq_state = "PQ_AUTHORIZATION_EXECUTABLE_DRAFT"
    else:
        pq_state = "PQ_AUTHORIZATION_SPEC_ONLY"

    if not pq_authorization.security_proof_complete:
        gaps.append("PQ authorization security proof is incomplete or not yet published as complete.")
    if not pq_authorization.test_vectors_complete:
        gaps.append("PQ authorization comprehensive test vectors are incomplete.")
    if not pq_authorization.production_implementation:
        gaps.append("PQ authorization lacks a production implementation.")
    if not pq_authorization.consensus_activated:
        gaps.append("PQ authorization/output mechanism is not consensus-active.")
    if pq_authorization.stateful_primary and not pq_authorization.stateless_fallback:
        gaps.append("Stateful signing path lacks a stateless recovery fallback.")

    if rescue.requires_pq_authorization and not pq_authorization.consensus_activated:
        rescue_state = "RESCUE_BLOCKED_ON_PQ_AUTHORIZATION"
        gaps.append("Rescue protocol requires an already-functioning PQ authorization/output destination.")
    elif rescue.consensus_activated:
        rescue_state = "RESCUE_CONSENSUS_ACTIVE"
    elif rescue.production_implementation:
        rescue_state = "RESCUE_IMPLEMENTED_NOT_ACTIVATED"
    else:
        rescue_state = "RESCUE_PROPOSAL_ONLY"

    if sunset.requires_pq_authorization and not pq_authorization.consensus_activated:
        sunset_state = "SUNSET_BLOCKED_ON_PQ_AUTHORIZATION"
        gaps.append("Legacy-signature sunset depends on a deployed PQ authorization/output mechanism.")
    elif sunset.consensus_activated:
        sunset_state = "SUNSET_CONSENSUS_ACTIVE"
    else:
        sunset_state = "SUNSET_DRAFT_OR_POLICY_ONLY"

    if pq_authorization.consensus_activated and rescue.consensus_activated and sunset.consensus_activated:
        deployment_state = "DEPLOYABLE_MITIGATION_STACK"
        urgency = "MAINTAIN_AND_EXERCISE"
    elif pq_authorization.reference_implementation and rescue.status.lower() in {"proposal", "draft"}:
        deployment_state = "DEPENDENCY_COMPLETE_RESEARCH_STACK"
        urgency = "ACCELERATE_SECURITY_PROOF_INTEROP_AND_ACTIVATION_PLANNING"
    else:
        deployment_state = "FRAGMENTED_MITIGATION_RESEARCH"
        urgency = "CONTINUE_PROTOCOL_DESIGN"

    return MitigationReadiness(
        pq_authorization_state=pq_state,
        rescue_state=rescue_state,
        sunset_state=sunset_state,
        deployment_state=deployment_state,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
    )

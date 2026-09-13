"""Defensive classifier for post-quantum institutional custody readiness.

This module tracks custody-layer migration evidence only. It does not access
wallets, sign transactions, recover keys, or interact with live networks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CustodyEvidence:
    name: str
    source: str
    regulated: bool = False
    deployed_exposure_controls: bool = False
    pq_signing_simulation: bool = False
    pq_signing_live_chain: bool = False
    hybrid_transport_in_production: bool = False
    pq_hsm_or_signer_support: bool = False
    blockchain_pq_authorization_available: bool = False
    independent_review_complete: bool = False


@dataclass(frozen=True)
class CustodyReadiness:
    custody_state: str
    chain_dependency_state: str
    urgency: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_custody_readiness(evidence: CustodyEvidence) -> CustodyReadiness:
    """Classify custody-layer PQ readiness without overclaiming chain safety."""

    gaps: list[str] = []

    if evidence.regulated and evidence.deployed_exposure_controls and evidence.pq_signing_simulation:
        custody_state = "REGULATED_CUSTODY_MIGRATION_OPERATIONALIZED"
    elif evidence.deployed_exposure_controls or evidence.hybrid_transport_in_production:
        custody_state = "PRODUCTION_MIGRATION_CONTROLS_PRESENT"
    elif evidence.pq_signing_simulation:
        custody_state = "PQ_SIGNING_PILOT_ONLY"
    else:
        custody_state = "PLANNING_OR_RESEARCH_ONLY"

    if evidence.blockchain_pq_authorization_available and evidence.pq_signing_live_chain:
        chain_state = "CHAIN_AUTHORIZATION_PATH_AVAILABLE"
    else:
        chain_state = "CHAIN_AUTHORIZATION_REMAINS_BOTTLENECK"
        gaps.append("Custody-side readiness does not by itself provide a live post-quantum authorization path on every supported blockchain.")

    if not evidence.pq_signing_live_chain:
        gaps.append("No production live-chain post-quantum custody signing path is established by this evidence record.")
    if not evidence.independent_review_complete:
        gaps.append("Independent review or certification of the end-to-end post-quantum custody path is incomplete or not established.")
    if not evidence.pq_hsm_or_signer_support:
        gaps.append("Post-quantum signer/HSM support is not demonstrated by this evidence record.")

    if custody_state == "REGULATED_CUSTODY_MIGRATION_OPERATIONALIZED":
        urgency = "ACCELERATE_CHAIN_INTEGRATION_AND_INDEPENDENT_VALIDATION"
    elif custody_state == "PRODUCTION_MIGRATION_CONTROLS_PRESENT":
        urgency = "EXPAND_PQ_SIGNING_AND_CHAIN_INTEROP"
    else:
        urgency = "CONTINUE_CUSTODY_MIGRATION_ENGINEERING"

    return CustodyReadiness(
        custody_state=custody_state,
        chain_dependency_state=chain_state,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
    )

"""Downgrade-resistant PQC suite negotiation for canonical authority contexts.

This module records the complete offered-suite transcript and requires selection
of the strongest locally governed suite that was actually offered.  It does not
perform networking, create keys, sign transactions, or authorize value movement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from security.qcrypto.hybrid_authority_migration import AuthorityLayer, MigrationRequirement
from security.qcrypto.pqc_algorithm_policy import REGISTRY, StandardizationState, validate_registry


@dataclass(frozen=True)
class SuiteSpec:
    suite_id: str
    requirement: MigrationRequirement
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None


SUITES: dict[str, SuiteSpec] = {
    "HYBRID-ECDSA-MLDSA": SuiteSpec(
        "HYBRID-ECDSA-MLDSA", MigrationRequirement.HYBRID_REQUIRED, "ECDSA", "ML-DSA"
    ),
    "HYBRID-ED25519-MLDSA": SuiteSpec(
        "HYBRID-ED25519-MLDSA", MigrationRequirement.HYBRID_REQUIRED, "ED25519", "ML-DSA"
    ),
    "PQ-MLDSA": SuiteSpec("PQ-MLDSA", MigrationRequirement.PQ_REQUIRED, None, "ML-DSA"),
    "PQ-SLHDSA": SuiteSpec("PQ-SLHDSA", MigrationRequirement.PQ_REQUIRED, None, "SLH-DSA"),
}


@dataclass(frozen=True)
class SuiteNegotiationPolicy:
    network_id: str
    authority_layer: AuthorityLayer
    minimum_requirement: MigrationRequirement
    preference_order: tuple[str, ...]
    policy_version: int


@dataclass(frozen=True)
class SuiteNegotiationRequest:
    network_id: str
    authority_layer: AuthorityLayer
    offered_suite_ids: tuple[str, ...]
    selected_suite_id: str
    peer_capabilities_digest: str
    policy_version: int


@dataclass(frozen=True)
class SuiteNegotiationDecision:
    verdict: str
    accepted: bool
    blockers: tuple[str, ...]
    selected_suite_id: str | None
    strongest_offered_suite_id: str | None
    negotiation_transcript_digest: str | None
    classical_algorithm_id: str | None
    pq_algorithm_id: str | None
    effective_requirement: str | None
    execution_authority: bool = False
    live_value_authorized: bool = False
    transaction_authorized: bool = False
    claim_boundary: str = (
        "Suite-negotiation policy result only; this binds capability/selection intent "
        "and does not authenticate a peer, verify a signature, authorize execution, "
        "or establish production protocol conformance."
    )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data


def _valid_digest(value: str) -> bool:
    if len(value) != 64 or value.lower() != value:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _validate_suite(spec: SuiteSpec) -> list[str]:
    blockers: list[str] = []
    if spec.classical_algorithm_id:
        classical = REGISTRY.get(spec.classical_algorithm_id)
        if classical is None or classical.pq_resistant:
            blockers.append(f"Suite {spec.suite_id} has an invalid classical algorithm slot.")
    if spec.pq_algorithm_id:
        pq = REGISTRY.get(spec.pq_algorithm_id)
        if pq is None or not pq.pq_resistant:
            blockers.append(f"Suite {spec.suite_id} has an invalid PQ algorithm slot.")
        elif pq.standardization_state is not StandardizationState.FINAL_FIPS:
            blockers.append(f"Suite {spec.suite_id} PQ algorithm is not finalized-FIPS in the registry.")
    if spec.requirement is MigrationRequirement.HYBRID_REQUIRED:
        if not spec.classical_algorithm_id or not spec.pq_algorithm_id:
            blockers.append(f"Hybrid suite {spec.suite_id} must contain classical and PQ algorithms.")
    if spec.requirement is MigrationRequirement.PQ_REQUIRED and not spec.pq_algorithm_id:
        blockers.append(f"PQ suite {spec.suite_id} must contain a PQ algorithm.")
    return blockers


def assess_suite_negotiation(
    request: SuiteNegotiationRequest,
    policy: SuiteNegotiationPolicy,
) -> SuiteNegotiationDecision:
    validate_registry()
    blockers: list[str] = []

    if request.network_id != policy.network_id:
        blockers.append("Negotiation network id does not match policy scope.")
    if request.authority_layer is not policy.authority_layer:
        blockers.append("Negotiation authority layer does not match policy scope.")
    if request.policy_version != policy.policy_version:
        blockers.append("Negotiation policy version does not match the governed version.")
    if request.policy_version < 1:
        blockers.append("Negotiation policy version must be positive.")
    if not _valid_digest(request.peer_capabilities_digest):
        blockers.append("Peer capabilities digest must be canonical lowercase SHA-256 text.")
    if not request.offered_suite_ids:
        blockers.append("At least one suite must be offered.")
    if len(set(request.offered_suite_ids)) != len(request.offered_suite_ids):
        blockers.append("Duplicate suite identifiers are not allowed in an offer.")

    unknown_offers = [suite for suite in request.offered_suite_ids if suite not in SUITES]
    if unknown_offers:
        blockers.append("Offer contains an unrecognized suite identifier.")
    if request.selected_suite_id not in request.offered_suite_ids:
        blockers.append("Selected suite was not present in the offered suite transcript.")
    if request.selected_suite_id not in SUITES:
        blockers.append("Selected suite is not in the controlled suite registry.")

    for suite_id in policy.preference_order:
        if suite_id not in SUITES:
            blockers.append("Policy preference order contains an unrecognized suite identifier.")
    if len(set(policy.preference_order)) != len(policy.preference_order):
        blockers.append("Policy preference order contains duplicate suite identifiers.")

    for suite_id in request.offered_suite_ids:
        spec = SUITES.get(suite_id)
        if spec is not None:
            blockers.extend(_validate_suite(spec))

    eligible_offered = [
        suite_id
        for suite_id in policy.preference_order
        if suite_id in request.offered_suite_ids
        and SUITES[suite_id].requirement >= policy.minimum_requirement
    ]
    strongest = eligible_offered[0] if eligible_offered else None
    if strongest is None:
        blockers.append("No offered suite satisfies the minimum migration requirement.")
    elif request.selected_suite_id != strongest:
        blockers.append("Selected suite is not the strongest governed suite offered; downgrade rejected.")

    selected = SUITES.get(request.selected_suite_id)
    if selected is not None and selected.requirement < policy.minimum_requirement:
        blockers.append("Selected suite is below the minimum migration requirement.")

    if blockers:
        verdict = (
            "SUITE_DOWNGRADE_REJECTED"
            if any("downgrade" in blocker.lower() for blocker in blockers)
            else "SUITE_NEGOTIATION_BLOCKED"
        )
        return SuiteNegotiationDecision(
            verdict=verdict,
            accepted=False,
            blockers=tuple(blockers),
            selected_suite_id=request.selected_suite_id if request.selected_suite_id in SUITES else None,
            strongest_offered_suite_id=strongest,
            negotiation_transcript_digest=None,
            classical_algorithm_id=selected.classical_algorithm_id if selected else None,
            pq_algorithm_id=selected.pq_algorithm_id if selected else None,
            effective_requirement=selected.requirement.name if selected else None,
        )

    assert selected is not None
    transcript = {
        "network_id": request.network_id,
        "authority_layer": request.authority_layer.value,
        "offered_suite_ids": list(request.offered_suite_ids),
        "selected_suite_id": request.selected_suite_id,
        "peer_capabilities_digest": request.peer_capabilities_digest,
        "policy_version": request.policy_version,
        "minimum_requirement": policy.minimum_requirement.name,
        "preference_order": list(policy.preference_order),
    }
    transcript_digest = sha256(
        json.dumps(transcript, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    return SuiteNegotiationDecision(
        verdict="SUITE_NEGOTIATION_ACCEPTED",
        accepted=True,
        blockers=(),
        selected_suite_id=selected.suite_id,
        strongest_offered_suite_id=strongest,
        negotiation_transcript_digest=transcript_digest,
        classical_algorithm_id=selected.classical_algorithm_id,
        pq_algorithm_id=selected.pq_algorithm_id,
        effective_requirement=selected.requirement.name,
    )

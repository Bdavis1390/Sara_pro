from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field

from .config_custody import ConfigurationSnapshot, create_snapshot
from .improvement_cycle import (
    ImprovementProposal,
    ImprovementRisk,
    ImprovementState,
    ImprovementTriggerKind,
)
from .qualification import CapabilityStatus, ReviewStatus, canonical_digest
from .recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    DiscoveryNode,
    route_node,
)


class ImprovementRoute(str, Enum):
    ECHO = "ECHO"
    PRE = "PRE"
    PRIME = "PRIME"
    PRIME_TEVV = "PRIME-TEVV"
    OVERWATCH = "OVERWATCH"
    RED_TEAM = "RED-TEAM"
    PARTNER_SCREENING = "PARTNER-SCREENING"
    CONFIG_CUSTODY = "CONFIG-CUSTODY"
    OMEGA = "WS-OMEGA"


class ImprovementRoutingEnvelope(BaseModel):
    schema: str = "ws-recursive-improvement-routing-1"
    improvement_id: str
    routes: list[ImprovementRoute] = Field(min_length=1)
    lineage_refs: list[str] = Field(min_length=1)
    custody_eligible: bool = False
    deployment_authorized: bool = False
    claim_promotion_performed: bool = False
    external_execution_performed: bool = False
    envelope_digest: str = ""


_TRIGGER_BY_DISCOVERY_KIND = {
    DiscoveryKind.DOMAIN: ImprovementTriggerKind.RESEARCH,
    DiscoveryKind.OBSERVATION: ImprovementTriggerKind.NEW_EVIDENCE,
    DiscoveryKind.HYPOTHESIS: ImprovementTriggerKind.RESEARCH,
    DiscoveryKind.CONTRADICTION: ImprovementTriggerKind.CONTRADICTION,
    DiscoveryKind.NEGATIVE_SPACE: ImprovementTriggerKind.RESEARCH,
    DiscoveryKind.EXPERIMENT: ImprovementTriggerKind.TEST_RESULT,
    DiscoveryKind.PARTNER: ImprovementTriggerKind.PARTNER_FEEDBACK,
    DiscoveryKind.OPPORTUNITY: ImprovementTriggerKind.OPPORTUNITY,
    DiscoveryKind.STANDARD: ImprovementTriggerKind.REQUIREMENT_DELTA,
    DiscoveryKind.PRIOR_ART: ImprovementTriggerKind.RESEARCH,
    DiscoveryKind.RISK: ImprovementTriggerKind.ANOMALY,
}

_CAPABILITY_BY_EVIDENCE_STATE = {
    DiscoveryEvidenceState.SOURCE_VERIFIED: CapabilityStatus.SUPPORTED_BY_LITERATURE,
    DiscoveryEvidenceState.CORROBORATED: CapabilityStatus.SUPPORTED_BY_LITERATURE,
    DiscoveryEvidenceState.SINGLE_SOURCE: CapabilityStatus.HYPOTHESIS,
    DiscoveryEvidenceState.SIMULATED: CapabilityStatus.SIMULATED_ONLY,
    DiscoveryEvidenceState.HYPOTHESIS: CapabilityStatus.HYPOTHESIS,
    DiscoveryEvidenceState.SPECULATIVE: CapabilityStatus.SPECULATIVE_EXTENSION,
    DiscoveryEvidenceState.CONFLICTING: CapabilityStatus.NOT_CURRENTLY_CLAIMED,
    DiscoveryEvidenceState.UNVERIFIED: CapabilityStatus.NOT_CURRENTLY_CLAIMED,
}

_RISK_BY_DISCOVERY_KIND = {
    DiscoveryKind.DOMAIN: ImprovementRisk.LOW,
    DiscoveryKind.OBSERVATION: ImprovementRisk.MODERATE,
    DiscoveryKind.HYPOTHESIS: ImprovementRisk.MODERATE,
    DiscoveryKind.CONTRADICTION: ImprovementRisk.HIGH,
    DiscoveryKind.NEGATIVE_SPACE: ImprovementRisk.MODERATE,
    DiscoveryKind.EXPERIMENT: ImprovementRisk.MODERATE,
    DiscoveryKind.PARTNER: ImprovementRisk.MODERATE,
    DiscoveryKind.OPPORTUNITY: ImprovementRisk.MODERATE,
    DiscoveryKind.STANDARD: ImprovementRisk.MODERATE,
    DiscoveryKind.PRIOR_ART: ImprovementRisk.HIGH,
    DiscoveryKind.RISK: ImprovementRisk.HIGH,
}


def _stable_improvement_id(node: DiscoveryNode, created_utc: str) -> str:
    year = created_utc[:4]
    if len(year) != 4 or not year.isdigit():
        raise ValueError("created_utc must begin with a four-digit year")
    material = {
        "node_id": node.node_id,
        "statement": node.statement,
        "source_refs": sorted(set(node.source_refs)),
        "created_year": year,
    }
    digest_hex = canonical_digest(material).split(":", 1)[1]
    numeric_suffix = str(int(digest_hex[:12], 16))
    return f"WS-IR-{year}-{numeric_suffix}"


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def omega_to_improvement(
    node: DiscoveryNode,
    *,
    created_utc: str,
    baseline_artifacts: Iterable[str] = (),
    additional_required_tests: Iterable[str] = (),
) -> ImprovementProposal:
    """Translate an OMEGA discovery into a governed WS-RI proposal.

    Translation preserves lineage and evidence state but does not elevate
    capability maturity, perform claim promotion, authorize external execution,
    or deploy any change.
    """

    trigger = _TRIGGER_BY_DISCOVERY_KIND[node.kind]
    baseline_status = _CAPABILITY_BY_EVIDENCE_STATE[node.evidence_state]
    lanes = _dedupe([*(node.downstream_routes or route_node(node.kind)), "WS-RI"])
    sources = _dedupe([node.node_id, *node.source_refs])

    required_tests = _dedupe(
        [
            f"{node.node_id}:source-evidence-gate",
            f"{node.node_id}:red-team-gate",
            *node.falsification_tests,
            *additional_required_tests,
        ]
    )

    risks = [
        "Discovery relevance or source interpretation may not transfer cleanly into the affected Worldshepherd lanes.",
        "No capability, readiness, partner-validation, certification, or physical-performance claim may be elevated from this translation alone.",
    ]
    if node.evidence_state in {
        DiscoveryEvidenceState.SINGLE_SOURCE,
        DiscoveryEvidenceState.HYPOTHESIS,
        DiscoveryEvidenceState.SPECULATIVE,
        DiscoveryEvidenceState.CONFLICTING,
        DiscoveryEvidenceState.UNVERIFIED,
    }:
        risks.append("Evidence is incomplete, conflicting, or not independently corroborated.")
    if node.cross_domain_tags:
        risks.append("Cross-domain applicability remains a hypothesis until receiving-lane qualification succeeds.")

    return ImprovementProposal(
        improvement_id=_stable_improvement_id(node, created_utc),
        trigger_kind=trigger,
        title=f"OMEGA improvement candidate: {node.domain}",
        source_refs=sources,
        affected_lanes=lanes,
        baseline_artifacts=_dedupe(baseline_artifacts),
        baseline_capability_status=[baseline_status],
        target_capability_status=None,
        proposed_change=(
            "Evaluate and, only if qualification succeeds, incorporate the following "
            f"OMEGA discovery into the affected Worldshepherd lanes: {node.statement}"
        ),
        expected_benefit=(
            "Close the traceable gap between recursive discovery and governed Worldshepherd change control while preserving evidence and claims boundaries."
        ),
        assumptions=[
            "The OMEGA node accurately represents its current evidence state and provenance references.",
            "Existing PRE, ECHO, TEVV, PRIME, and configuration-custody controls remain authoritative.",
        ],
        risks=risks,
        risk_level=_RISK_BY_DISCOVERY_KIND[node.kind],
        required_tests=required_tests,
        success_metrics=[
            "All required validation tests return PASS.",
            "No claims-boundary violation is introduced.",
            "No unauthorized external execution occurs.",
            "Affected-lane evidence and configuration lineage remain traceable.",
        ],
        negative_evidence=[],
        reversible=True,
        generated_by="WS-OMEGA->WS-RI",
        created_utc=created_utc,
        state=ImprovementState.PROPOSED,
        requested_claim_promotion=False,
        requested_external_execution=False,
    )


def route_improvement(proposal: ImprovementProposal) -> ImprovementRoutingEnvelope:
    """Produce deterministic downstream routes without executing any route."""

    routes: list[ImprovementRoute] = [
        ImprovementRoute.ECHO,
        ImprovementRoute.OMEGA,
        ImprovementRoute.PRIME_TEVV,
    ]

    if proposal.trigger_kind in {
        ImprovementTriggerKind.REQUIREMENT_DELTA,
        ImprovementTriggerKind.OPPORTUNITY,
        ImprovementTriggerKind.PARTNER_FEEDBACK,
        ImprovementTriggerKind.RESEARCH,
        ImprovementTriggerKind.NEW_EVIDENCE,
    }:
        routes.append(ImprovementRoute.PRE)

    if proposal.trigger_kind in {
        ImprovementTriggerKind.FAILURE,
        ImprovementTriggerKind.ANOMALY,
        ImprovementTriggerKind.CONTRADICTION,
        ImprovementTriggerKind.SECURITY_EVENT,
        ImprovementTriggerKind.TEST_RESULT,
    }:
        routes.extend([ImprovementRoute.PRIME, ImprovementRoute.OVERWATCH, ImprovementRoute.RED_TEAM])

    if proposal.trigger_kind in {
        ImprovementTriggerKind.PARTNER_FEEDBACK,
        ImprovementTriggerKind.OPPORTUNITY,
    }:
        routes.append(ImprovementRoute.PARTNER_SCREENING)

    custody_eligible = proposal.state == ImprovementState.PROMOTED
    if custody_eligible:
        routes.append(ImprovementRoute.CONFIG_CUSTODY)

    unique_routes = list(dict.fromkeys(routes))
    lineage = _dedupe([proposal.improvement_id, *proposal.source_refs, *proposal.review.qualification_refs])
    payload = {
        "schema": "ws-recursive-improvement-routing-1",
        "improvement_id": proposal.improvement_id,
        "routes": [route.value for route in unique_routes],
        "lineage_refs": lineage,
        "custody_eligible": custody_eligible,
        "deployment_authorized": False,
        "claim_promotion_performed": False,
        "external_execution_performed": False,
    }
    return ImprovementRoutingEnvelope(
        improvement_id=proposal.improvement_id,
        routes=unique_routes,
        lineage_refs=lineage,
        custody_eligible=custody_eligible,
        deployment_authorized=False,
        claim_promotion_performed=False,
        external_execution_performed=False,
        envelope_digest=canonical_digest(payload),
    )


def build_promoted_configuration_snapshot(
    proposal: ImprovementProposal,
    *,
    candidate_payload: dict,
    snapshot_id: str,
    created_utc: str,
    actor: str,
    parent_digest: str | None,
) -> ConfigurationSnapshot:
    """Stage a configuration-custody snapshot for a promoted improvement.

    This returns a snapshot only. It does not append to a custody ledger,
    merge code, deploy a release, actuate hardware, or execute any external
    action. The caller must still use the existing authorized custody/change
    path.
    """

    if proposal.state != ImprovementState.PROMOTED:
        raise ValueError("configuration custody requires a PROMOTED improvement record")
    if proposal.review.status != ReviewStatus.ACCEPTED:
        raise ValueError("configuration custody requires accepted human review")
    if not proposal.review.authorization_ref:
        raise ValueError("configuration custody requires an authorization reference")
    if not proposal.review.qualification_refs:
        raise ValueError("configuration custody requires qualification evidence")
    if not actor.strip():
        raise ValueError("configuration custody requires an identified actor")

    reason = (
        f"Stage promoted Worldshepherd improvement {proposal.improvement_id}; "
        f"authorization={proposal.review.authorization_ref}; "
        f"qualification={','.join(proposal.review.qualification_refs)}"
    )
    return create_snapshot(
        snapshot_id=snapshot_id,
        payload=dict(candidate_payload),
        created_utc=created_utc,
        actor=actor,
        reason=reason,
        parent_digest=parent_digest,
    )

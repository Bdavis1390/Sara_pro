"""Governed Worldshepherd control-plane for PQC migration planning.

This module connects the evidence-custodied CBOM model to the Worldshepherd
SARA/ECHO/PRIME/OVERWATCH governance pattern. It is deliberately non-invasive:
it does not alter cryptographic configurations, rotate keys, deploy software,
or claim Federal compliance. It produces bounded migration-plan decisions only.
"""

from __future__ import annotations

from dataclasses import dataclass

from cbom_inventory import CryptoAsset, priority_band, validate_asset


CLAIM_BOUNDARY = "INTERNAL_PQC_CONTROL_PLANE_NOT_FEDERAL_COMPLIANCE"
AUDIT_PROJECTION_SCHEMA = "WS-QCRYPTO-CONTROL-DECISION-V1"


@dataclass(frozen=True)
class ControlPlaneDecision:
    asset_id: str
    echo_state: str
    prime_state: str
    sara_state: str
    overwatch_state: str
    priority: str
    human_approval_required: bool
    migration_executed: bool
    claim_boundary: str = CLAIM_BOUNDARY


def evaluate_asset(
    asset: CryptoAsset,
    *,
    human_approved: bool = False,
) -> ControlPlaneDecision:
    """Evaluate one CBOM record through ECHO -> PRIME -> SARA -> OVERWATCH.

    The function never performs a migration. `human_approved=True` records that
    SARA may authorize a bounded migration *plan* for downstream execution by an
    appropriately authorized operator/system. `migration_executed` therefore
    remains False by construction.
    """
    missing = validate_asset(asset)
    if missing:
        return ControlPlaneDecision(
            asset_id=asset.asset_id or "UNIDENTIFIED",
            echo_state="ECHO_REJECTED_INCOMPLETE_EVIDENCE",
            prime_state="PRIME_NOT_EVALUATED",
            sara_state="SARA_BLOCKED",
            overwatch_state="OVERWATCH_EVIDENCE_GAP",
            priority="INCOMPLETE_EVIDENCE",
            human_approval_required=True,
            migration_executed=False,
        )

    priority = priority_band(asset)
    echo_state = "ECHO_PROVENANCE_ACCEPTED"

    if priority in {"P0_MIGRATION_PRIORITY", "P1_MIGRATION_PRIORITY"}:
        prime_state = "PRIME_RECOMMENDS_PRIORITY_MIGRATION_PLAN"
    elif priority == "P2_MODERNIZATION_PRIORITY":
        prime_state = "PRIME_RECOMMENDS_MODERNIZATION_PLAN"
    else:
        prime_state = "PRIME_RECOMMENDS_MONITOR"

    if human_approved:
        sara_state = "SARA_PLAN_AUTHORIZED"
        overwatch_state = "OVERWATCH_TRACK_AUTHORIZED_PLAN"
    else:
        sara_state = "SARA_AWAITING_HUMAN_APPROVAL"
        overwatch_state = "OVERWATCH_TRACK_PENDING_APPROVAL"

    return ControlPlaneDecision(
        asset_id=asset.asset_id,
        echo_state=echo_state,
        prime_state=prime_state,
        sara_state=sara_state,
        overwatch_state=overwatch_state,
        priority=priority,
        human_approval_required=True,
        migration_executed=False,
    )


def audit_projection(
    decision: ControlPlaneDecision,
    *,
    correlation_id: str | None = None,
) -> dict[str, object]:
    """Project a decision into the data-only SARA audit bridge contract.

    This mapping carries governance state only. It intentionally contains
    explicit negative authority/compliance flags so downstream persistence
    cannot be mistaken for migration execution, live-value authorization,
    Federal compliance, or WS-CAE conformance.
    """
    projection: dict[str, object] = {
        "schema": AUDIT_PROJECTION_SCHEMA,
        "asset_id": decision.asset_id,
        "echo_state": decision.echo_state,
        "prime_state": decision.prime_state,
        "sara_state": decision.sara_state,
        "overwatch_state": decision.overwatch_state,
        "priority": decision.priority,
        "human_approval_required": decision.human_approval_required,
        "migration_executed": decision.migration_executed,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": decision.claim_boundary,
    }
    if correlation_id is not None:
        if not isinstance(correlation_id, str) or not correlation_id:
            raise ValueError("correlation_id must be a non-empty string when supplied")
        projection["correlation_id"] = correlation_id
    return projection


def portfolio_status(
    assets: tuple[CryptoAsset, ...],
    *,
    approved_asset_ids: frozenset[str] = frozenset(),
) -> dict[str, object]:
    decisions = tuple(
        evaluate_asset(asset, human_approved=asset.asset_id in approved_asset_ids)
        for asset in assets
    )
    return {
        "asset_count": len(decisions),
        "authorized_plan_count": sum(d.sara_state == "SARA_PLAN_AUTHORIZED" for d in decisions),
        "pending_approval_count": sum(d.sara_state == "SARA_AWAITING_HUMAN_APPROVAL" for d in decisions),
        "evidence_gap_count": sum(d.priority == "INCOMPLETE_EVIDENCE" for d in decisions),
        "migration_execution_count": sum(d.migration_executed for d in decisions),
        "decisions": decisions,
        "claim_boundary": CLAIM_BOUNDARY,
    }

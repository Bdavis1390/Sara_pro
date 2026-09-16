"""Bridge Federal PQC migration priority into Worldshepherd's WS-CAE-1 pilot.

The bridge recommends a target profile and safe pilot entry stage only. It does
not claim WS-CAE-1 conformance, Federal compliance, production readiness, or
permission to move live value.
"""

from __future__ import annotations

from dataclasses import dataclass

from cbom_inventory import CryptoAsset
from federal_pqc_control_plane import evaluate_asset


CLAIM_BOUNDARY = "PILOT_TARGET_RECOMMENDATION_NOT_CONFORMANCE_OR_COMPLIANCE"


@dataclass(frozen=True)
class PilotTarget:
    asset_id: str
    priority: str
    target_cae_profile: str
    pilot_entry_stage: str
    next_evidence: tuple[str, ...]
    human_approval_required: bool
    live_value_authorized: bool = False
    conformance_established: bool = False
    federal_compliance_established: bool = False
    claim_boundary: str = CLAIM_BOUNDARY


def recommend_pilot_target(
    asset: CryptoAsset,
    *,
    human_approved: bool = False,
) -> PilotTarget:
    decision = evaluate_asset(asset, human_approved=human_approved)

    if decision.priority == "INCOMPLETE_EVIDENCE":
        return PilotTarget(
            asset_id=decision.asset_id,
            priority=decision.priority,
            target_cae_profile="CAE-C0_DOCUMENTED_AUTHORITY",
            pilot_entry_stage="H0_EVIDENCE_QUALIFICATION_BLOCKED",
            next_evidence=(
                "complete CBOM provenance",
                "identify owner and cryptographic role",
                "record verification timestamp",
            ),
            human_approval_required=True,
        )

    if decision.priority in {"P0_MIGRATION_PRIORITY", "P1_MIGRATION_PRIORITY"}:
        target = "CAE-C3_DIVERSIFIED_HIGH_VALUE_AUTHORITY"
        evidence = (
            "stable authority identifier",
            "replaceable authenticators",
            "versioned policy and explicit human approval",
            "recovery commitment and non-production recovery exercise",
            "algorithm-family diversity or explicit risk acceptance",
            "provider-diversity assessment",
        )
    elif decision.priority == "P2_MODERNIZATION_PRIORITY":
        target = "CAE-C2_RECOVERABLE_DOMAIN_BOUND"
        evidence = (
            "stable authority identifier",
            "replaceable authenticator mechanism",
            "versioned policy",
            "domain/replay binding",
            "recovery commitment and non-production recovery exercise",
        )
    else:
        target = "CAE-C1_CRYPTO_AGILE_AUTHORITY"
        evidence = (
            "maintain CBOM freshness",
            "retain algorithm-agility evidence",
            "monitor provider and dependency changes",
        )

    stage = "H1_ZERO_VALUE_DRY_RUN" if human_approved else "H0_EVIDENCE_QUALIFICATION"

    return PilotTarget(
        asset_id=decision.asset_id,
        priority=decision.priority,
        target_cae_profile=target,
        pilot_entry_stage=stage,
        next_evidence=evidence,
        human_approval_required=True,
    )


def portfolio_pilot_targets(
    assets: tuple[CryptoAsset, ...],
    *,
    approved_asset_ids: frozenset[str] = frozenset(),
) -> dict[str, object]:
    targets = tuple(
        recommend_pilot_target(asset, human_approved=asset.asset_id in approved_asset_ids)
        for asset in assets
    )
    return {
        "asset_count": len(targets),
        "h0_count": sum(t.pilot_entry_stage.startswith("H0_") for t in targets),
        "h1_count": sum(t.pilot_entry_stage == "H1_ZERO_VALUE_DRY_RUN" for t in targets),
        "live_value_authorized_count": sum(t.live_value_authorized for t in targets),
        "conformance_established_count": sum(t.conformance_established for t in targets),
        "federal_compliance_established_count": sum(t.federal_compliance_established for t in targets),
        "targets": targets,
        "claim_boundary": CLAIM_BOUNDARY,
    }

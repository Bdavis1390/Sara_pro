"""Defensive classifier for sector-level post-quantum migration coordination.

Tracks whether post-quantum migration has moved from isolated institutional work
to coordinated financial-sector transition. It does not infer Q-day, impose
regulatory requirements, or claim blockchain-level quantum safety.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SectorCoordinationEvidence:
    name: str
    source: str
    federal_policy_active: bool = False
    public_private_task_force_active: bool = False
    digital_assets_explicitly_in_scope: bool = False
    third_party_vendor_readiness_workstream: bool = False
    cross_border_g7_roadmap: bool = False
    crypto_specific_binding_deadline: bool = False
    blockchain_pq_activation_required: bool = False
    qday_demonstrated: bool = False


@dataclass(frozen=True)
class SectorCoordinationAssessment:
    coordination_state: str
    digital_asset_state: str
    mandate_state: str
    urgency: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_sector_coordination(evidence: SectorCoordinationEvidence) -> SectorCoordinationAssessment:
    """Classify sector-level PQ migration without overclaiming regulation or Q-day."""

    gaps: list[str] = []

    if (
        evidence.federal_policy_active
        and evidence.public_private_task_force_active
        and evidence.cross_border_g7_roadmap
    ):
        coordination = "FINANCIAL_SECTOR_COORDINATED_PQ_TRANSITION"
    elif evidence.public_private_task_force_active:
        coordination = "DOMESTIC_SECTOR_COORDINATION_ACTIVE"
    else:
        coordination = "INSTITUTION_LEVEL_OR_EARLY_COORDINATION"

    if evidence.digital_assets_explicitly_in_scope:
        digital_assets = "DIGITAL_ASSETS_EXPLICITLY_IN_SCOPE"
    else:
        digital_assets = "DIGITAL_ASSET_SCOPE_NOT_ESTABLISHED"
        gaps.append("Digital assets are not explicitly established as a sector-level workstream in this evidence record.")

    if evidence.crypto_specific_binding_deadline:
        mandate = "CRYPTO_SPECIFIC_BINDING_DEADLINE_PRESENT"
    else:
        mandate = "COORDINATION_WITHOUT_CRYPTO_SPECIFIC_BINDING_DEADLINE"
        gaps.append("No crypto-specific binding PQ migration deadline is established by this evidence record.")

    if evidence.blockchain_pq_activation_required:
        gaps.append("Sector coordination does not substitute for chain-native post-quantum transaction authorization or consensus activation.")

    if not evidence.qday_demonstrated:
        gaps.append("The coordination program is not evidence that a cryptographically relevant quantum computer or Q-day has been demonstrated.")

    if coordination == "FINANCIAL_SECTOR_COORDINATED_PQ_TRANSITION" and digital_assets == "DIGITAL_ASSETS_EXPLICITLY_IN_SCOPE":
        urgency = "ALIGN_CHAIN_CUSTODY_STABLECOIN_BRIDGE_MIGRATION_WITH_SECTOR_PROGRAM"
    else:
        urgency = "CONTINUE_SECTOR_ALIGNMENT"

    return SectorCoordinationAssessment(
        coordination_state=coordination,
        digital_asset_state=digital_assets,
        mandate_state=mandate,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
    )

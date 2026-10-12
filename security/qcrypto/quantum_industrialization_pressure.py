"""Defensive classifier for simultaneous quantum industrialization and PQ migration pressure.

This module tracks whether public investment and manufacturing programs are accelerating
fault-tolerant quantum-computing capability while public-sector programs simultaneously
accelerate defensive post-quantum migration. It does not infer Q-day, predict vendor
roadmap success, or estimate private-key recovery capability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class IndustrializationEvidence:
    name: str
    source: str
    federal_quantum_funding_active: bool = False
    manufacturing_scale_program_active: bool = False
    fault_tolerant_vendor_awards_active: bool = False
    financial_sector_pq_transition_active: bool = False
    digital_assets_in_defensive_scope: bool = False
    demonstrated_cryptanalytic_break: bool = False
    production_attack_machine_demonstrated: bool = False


@dataclass(frozen=True)
class IndustrializationAssessment:
    strategic_state: str
    offensive_side_state: str
    defensive_side_state: str
    urgency: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_quantum_industrialization(evidence: IndustrializationEvidence) -> IndustrializationAssessment:
    """Classify system-level co-acceleration without turning funding into Q-day claims."""

    gaps: list[str] = []

    attack_side = (
        evidence.federal_quantum_funding_active
        and evidence.manufacturing_scale_program_active
        and evidence.fault_tolerant_vendor_awards_active
    )
    defense_side = evidence.financial_sector_pq_transition_active and evidence.digital_assets_in_defensive_scope

    if attack_side and defense_side:
        strategic_state = "ATTACK_DEFENSE_CO_ACCELERATION"
        urgency = "COMPRESS_MIGRATION_TIMELINES_AND_TRACK_INDUSTRIAL_CAPACITY"
    elif attack_side:
        strategic_state = "QUANTUM_INDUSTRIALIZATION_ACCELERATING"
        urgency = "ACCELERATE_DEFENSIVE_MIGRATION"
    elif defense_side:
        strategic_state = "DEFENSIVE_SECTOR_MIGRATION_ACCELERATING"
        urgency = "MAINTAIN_DEFENSIVE_TRANSITION"
    else:
        strategic_state = "EARLY_OR_FRAGMENTED_TRANSITION"
        urgency = "CONTINUE_MONITORING"

    offensive_side_state = (
        "INDUSTRIAL_SCALE_ENABLERS_ACTIVE" if attack_side else "INDUSTRIAL_SCALE_ENABLERS_INCOMPLETE"
    )
    defensive_side_state = (
        "COORDINATED_FINANCIAL_PQ_MIGRATION_ACTIVE"
        if defense_side
        else "DEFENSIVE_COORDINATION_INCOMPLETE"
    )

    if not evidence.production_attack_machine_demonstrated:
        gaps.append("No production cryptanalytic attack machine is demonstrated by this evidence record.")
    if not evidence.demonstrated_cryptanalytic_break:
        gaps.append("No production cryptographic break is demonstrated by this evidence record.")
    if attack_side:
        gaps.append("Funding and manufacturing capacity are leading indicators; they do not guarantee vendor roadmap delivery.")
    if defense_side:
        gaps.append("Sector migration coordination does not substitute for chain-native PQ authorization and consensus migration.")

    return IndustrializationAssessment(
        strategic_state=strategic_state,
        offensive_side_state=offensive_side_state,
        defensive_side_state=defensive_side_state,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
    )

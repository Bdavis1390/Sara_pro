"""Worldshepherd QCRYPTO width-time-exposure risk gate.

This module is defensive analysis only. It does not implement key recovery,
Shor's algorithm, wallet interaction, transaction signing, or network access.
It converts externally published resource estimates into claims-controlled
risk states for migration planning.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class AttackEstimate:
    name: str
    source: str
    full_attack: bool
    logical_qubits: int
    toffoli_gates: int
    physical_qubits: Optional[int] = None
    runtime_seconds: Optional[float] = None
    production_break_demonstrated: bool = False

    @property
    def gate_width_product(self) -> int:
        """Coarse comparison proxy only; Toffoli count is not circuit depth."""
        return self.logical_qubits * self.toffoli_gates


@dataclass(frozen=True)
class RiskAssessment:
    threat_level: str
    claim_state: str
    width_band: str
    attack_exposure_ratio: Optional[float]
    migration_margin_days: Optional[float]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def width_band(logical_qubits: int) -> str:
    if logical_qubits <= 900:
        return "VERY_LOW_WIDTH"
    if logical_qubits <= 1500:
        return "LOW_WIDTH"
    if logical_qubits <= 3000:
        return "MODERATE_WIDTH"
    return "HIGH_WIDTH"


def assess(
    estimate: AttackEstimate,
    *,
    exposure_seconds: Optional[float] = None,
    warning_days: Optional[float] = None,
    migration_days: Optional[float] = None,
) -> RiskAssessment:
    """Return a claims-controlled Q0-Q4 assessment.

    Q0: mathematical/resource issue known, no operational overlap shown.
    Q1: materially compressed attack resources; accelerated validation required.
    Q2: modeled complete attack runtime overlaps the public-key exposure window.
    Q3: Q2 plus migration margin is exhausted/negative.
    Q4: production-strength break demonstrated in a controlled, authorized setting.

    A low logical-qubit count alone can never produce Q2+. This deliberately
    separates *width* from *time* and prevents low-width/high-gate constructions
    from being misreported as fast attacks.
    """
    reasons: list[str] = []
    band = width_band(estimate.logical_qubits)
    ratio: Optional[float] = None
    margin: Optional[float] = None

    if estimate.production_break_demonstrated:
        return RiskAssessment(
            threat_level="Q4",
            claim_state="PRODUCTION_BREAK_DEMONSTRATED",
            width_band=band,
            attack_exposure_ratio=None,
            migration_margin_days=None,
            reasons=("Production-strength break flag is set.",),
        )

    level = "Q0"
    claim_state = "RESOURCE_ESTIMATE_ONLY"

    if estimate.full_attack and estimate.logical_qubits <= 1500:
        level = "Q1"
        claim_state = "COMPLETE_ATTACK_RESOURCE_ESTIMATE"
        reasons.append("Complete ECDLP/Shor estimate has compressed logical width.")
    elif not estimate.full_attack:
        reasons.append("Estimate is a subroutine/component result, not an end-to-end attack.")

    if estimate.toffoli_gates >= 1_000_000_000:
        reasons.append("Very high Toffoli count: low width does not imply low runtime.")

    if (
        estimate.full_attack
        and estimate.runtime_seconds is not None
        and exposure_seconds is not None
        and exposure_seconds > 0
    ):
        ratio = estimate.runtime_seconds / exposure_seconds
        if ratio <= 1.0:
            level = "Q2"
            claim_state = "MODELED_ATTACK_OVERLAPS_EXPOSURE"
            reasons.append("Modeled complete attack runtime is within the key exposure window.")
        else:
            reasons.append("Modeled attack runtime exceeds the supplied exposure window.")

    if warning_days is not None and migration_days is not None:
        margin = warning_days - migration_days
        if level == "Q2" and margin <= 0:
            level = "Q3"
            claim_state = "MIGRATION_MARGIN_EXHAUSTED"
            reasons.append("Migration cannot complete within the supplied warning horizon.")
        elif margin <= 0:
            reasons.append("Migration margin is non-positive, but no operational attack-overlap evidence was supplied.")

    if not reasons:
        reasons.append("No operational overlap demonstrated; continue monitoring and migration preparation.")

    return RiskAssessment(
        threat_level=level,
        claim_state=claim_state,
        width_band=band,
        attack_exposure_ratio=ratio,
        migration_margin_days=margin,
        reasons=tuple(reasons),
    )

"""Worldshepherd QCRYPTO width-time-exposure, QEC and roadmap risk gate.

Defensive analysis only. This module does not implement key recovery, Shor's
algorithm, wallet interaction, transaction signing, or network access. It
converts externally published resource estimates, measured QEC evidence and
vendor hardware roadmaps into claims-controlled states for migration planning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
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
class QECEvidence:
    """Measured QEC evidence for one concrete code/hardware configuration.

    `physical_qubits` / `logical_qubits` is a measured code-block ratio only.
    It is NOT a full-application physical-qubit estimate because ancillas,
    factories, routing, decoding, code switching and runtime reliability can
    dominate a complete fault-tolerant workload.
    """

    name: str
    source: str
    physical_qubits: int
    logical_qubits: int
    code_distance: Optional[int] = None
    logical_memory_error_per_cycle: Optional[float] = None
    logical_clifford_error: Optional[float] = None
    postselection_used: bool = False
    universal_non_clifford_demonstrated: bool = False
    architecture_specific_attack_compilation: bool = False
    attack_scale_demonstrated: bool = False
    complete_fault_tolerant_overhead_model: bool = False
    independently_replicated: bool = False

    @property
    def physical_per_logical(self) -> float:
        if self.logical_qubits <= 0 or self.physical_qubits <= 0:
            raise ValueError("QEC qubit counts must be positive")
        return self.physical_qubits / self.logical_qubits


@dataclass(frozen=True)
class HardwareRoadmapTarget:
    """Forward-looking hardware target.

    Roadmaps are planning evidence, not demonstrated capability. The
    `same_architecture_family` flag means a physical-resource comparison is
    technically relevant enough to monitor; it does not prove that the future
    target will implement the exact attack/QEC stack or meet its runtime.
    """

    vendor: str
    source: str
    target_year: int
    physical_qubits: Optional[int] = None
    logical_qubits: Optional[int] = None
    logical_error_rate: Optional[float] = None
    same_architecture_family: bool = False
    demonstrated: bool = False


@dataclass(frozen=True)
class QECBridgeAssessment:
    evidence_state: str
    physical_per_logical: float
    codeblock_floor_physical_qubits: int
    attack_projection_state: str
    blocking_gaps: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RoadmapCollisionAssessment:
    collision_state: str
    evidence_state: str
    target_year: int
    years_to_target: int
    logical_headroom: Optional[int]
    physical_headroom: Optional[int]
    migration_margin_years: Optional[float]
    urgency: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


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


def assess_qec_bridge(estimate: AttackEstimate, qec: QECEvidence) -> QECBridgeAssessment:
    """Assess whether measured QEC evidence can be bridged to an attack estimate.

    The code-block floor is intentionally reported as a lower-bound arithmetic
    comparison only. It must never be described as the physical resources for
    the complete attack unless architecture-specific compilation, universal
    non-Clifford execution, attack-scale operation and a complete FT overhead
    model are all available.
    """

    ratio = qec.physical_per_logical
    floor = ceil(estimate.logical_qubits * ratio)
    gaps: list[str] = []

    if not estimate.full_attack:
        gaps.append("Attack estimate is not end-to-end.")
    if not qec.universal_non_clifford_demonstrated:
        gaps.append("Universal non-Clifford fault-tolerant execution is not demonstrated for this evidence record.")
    if not qec.architecture_specific_attack_compilation:
        gaps.append("No architecture-specific compilation of this attack to the measured QEC architecture is supplied.")
    if not qec.attack_scale_demonstrated:
        gaps.append("The QEC architecture has not been demonstrated at the attack's logical width and workload scale.")
    if not qec.complete_fault_tolerant_overhead_model:
        gaps.append("Ancilla, magic-state/factory, routing, decoding and runtime-reliability overheads are not completely modeled.")

    if qec.postselection_used:
        evidence_state = "QEC_DEMONSTRATED_WITH_POSTSELECTION"
    elif qec.logical_memory_error_per_cycle is not None or qec.logical_clifford_error is not None:
        evidence_state = "HARDWARE_VALIDATED_QEC_WITHOUT_POSTSELECTION"
    else:
        evidence_state = "QEC_RESOURCE_RECORD_ONLY"

    projection_state = (
        "MODEL_READY_NOT_PRODUCTION_BREAK"
        if not gaps
        else "CROSS_ARCHITECTURE_PROJECTION_BLOCKED"
    )

    return QECBridgeAssessment(
        evidence_state=evidence_state,
        physical_per_logical=ratio,
        codeblock_floor_physical_qubits=floor,
        attack_projection_state=projection_state,
        blocking_gaps=tuple(gaps),
    )


def assess_roadmap_collision(
    estimate: AttackEstimate,
    roadmap: HardwareRoadmapTarget,
    *,
    current_year: int,
    migration_years: Optional[float] = None,
) -> RoadmapCollisionAssessment:
    """Compare a published attack envelope with a forward hardware roadmap.

    This function is intentionally conservative. A roadmap collision can raise
    migration urgency, but it can never establish Q2/Q3/Q4 or a production
    break because a roadmap is not demonstrated hardware.
    """

    reasons: list[str] = []
    years_to_target = roadmap.target_year - current_year
    logical_headroom: Optional[int] = None
    physical_headroom: Optional[int] = None
    migration_margin_years: Optional[float] = None

    if roadmap.logical_qubits is not None:
        logical_headroom = roadmap.logical_qubits - estimate.logical_qubits
    if roadmap.physical_qubits is not None and estimate.physical_qubits is not None:
        physical_headroom = roadmap.physical_qubits - estimate.physical_qubits

    logical_collision = logical_headroom is not None and logical_headroom >= 0
    near_logical_collision = logical_headroom is not None and -50 <= logical_headroom < 0
    physical_collision = (
        roadmap.same_architecture_family
        and physical_headroom is not None
        and physical_headroom >= 0
    )

    if (
        logical_collision
        and physical_collision
        and roadmap.same_architecture_family
        and estimate.runtime_seconds is not None
    ):
        collision_state = "SAME_ARCHITECTURE_ATTACK_ENVELOPE_COLLISION"
        reasons.append("Roadmap logical and physical targets overlap the published same-architecture attack envelope.")
    elif logical_collision and roadmap.same_architecture_family:
        collision_state = "SAME_ARCHITECTURE_LOGICAL_WIDTH_COLLISION"
        reasons.append("Roadmap logical width reaches the published attack width, but the complete physical/runtime envelope is not established.")
    elif logical_collision:
        collision_state = "CROSS_ARCHITECTURE_LOGICAL_WIDTH_COLLISION"
        reasons.append("Roadmap logical width reaches the published attack width, but architectures are not directly interchangeable.")
    elif near_logical_collision:
        collision_state = "NEAR_LOGICAL_WIDTH_COLLISION"
        reasons.append("Roadmap target is within 50 logical qubits of the published attack width.")
    else:
        collision_state = "NO_COLLISION"
        reasons.append("Roadmap target does not reach the published attack width.")

    evidence_state = "DEMONSTRATED_HARDWARE_CAPABILITY" if roadmap.demonstrated else "VENDOR_ROADMAP_TARGET"

    if migration_years is not None:
        migration_margin_years = years_to_target - migration_years

    urgency = "MONITOR"
    if collision_state != "NO_COLLISION":
        urgency = "PREPARE_MIGRATION"
        if years_to_target <= 2:
            urgency = "ACCELERATE_MIGRATION_VALIDATION"
        if migration_margin_years is not None and migration_margin_years <= 0:
            urgency = "MIGRATION_SCHEDULE_AT_RISK"

    if not roadmap.demonstrated:
        reasons.append("Roadmap target is forward-looking and cannot be treated as demonstrated cryptanalytic capability.")
    if roadmap.same_architecture_family:
        reasons.append("Same-architecture comparison is relevant for planning but still requires future hardware, QEC and runtime validation.")

    return RoadmapCollisionAssessment(
        collision_state=collision_state,
        evidence_state=evidence_state,
        target_year=roadmap.target_year,
        years_to_target=years_to_target,
        logical_headroom=logical_headroom,
        physical_headroom=physical_headroom,
        migration_margin_years=migration_margin_years,
        urgency=urgency,
        reasons=tuple(reasons),
    )


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

    Low logical-qubit count, low QEC code-block overhead, or a forward hardware
    roadmap alone can never produce Q2+. This separates width, time, QEC
    overhead, roadmap maturity and application-scale fault-tolerant execution so
    cross-paper arithmetic cannot become a false operational claim.
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

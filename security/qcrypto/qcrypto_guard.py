"""Worldshepherd QCRYPTO defensive convergence and migration-risk gate.

This module does not implement key recovery, Shor's algorithm, wallet access,
transaction signing, or network probing. It converts published attack-resource
estimates, measured QEC evidence, vendor roadmaps, platform/manufacturing
progress, and classical-decoder evidence into claims-controlled migration
signals.
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
    """Measured QEC evidence for one concrete code/hardware configuration."""

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
    """Forward-looking hardware target; never equivalent to delivered hardware."""

    vendor: str
    source: str
    target_year: int
    physical_qubits: Optional[int] = None
    logical_qubits: Optional[int] = None
    logical_error_rate: Optional[float] = None
    same_architecture_family: bool = False
    demonstrated: bool = False


@dataclass(frozen=True)
class PlatformMaturityEvidence:
    """Evidence that a roadmap platform has moved beyond slideware.

    This record describes demonstrated component/platform progress only. It does
    not imply target-scale fault tolerance or cryptanalytic capability.
    """

    vendor: str
    source: str
    platform: str
    physical_qubits: int
    qpu_fabricated: bool = False
    qubits_trapped_or_operated: bool = False
    customer_orders_open: bool = False
    customer_delivery_year: Optional[int] = None
    qec_component_validated_on_related_hardware: bool = False
    same_architecture_family: bool = False
    target_scale_demonstrated: bool = False


@dataclass(frozen=True)
class ClassicalDecoderEvidence:
    """Classical real-time decoder capacity relevant to fault-tolerant QEC.

    Proposed FPGA/ASIC capacity is planning evidence only. It cannot be treated
    as attack-ready unless hardware is demonstrated, the exact QEC family is
    compatible, and attack-specific integration is validated.
    """

    name: str
    source: str
    code_family: str
    supported_logical_qubits: int
    implementation_kind: str
    demonstrated_hardware: bool = False
    workload_processed_fraction: Optional[float] = None
    decoder_utilization_reduction: Optional[float] = None
    exact_attack_code_compatible: bool = False
    attack_specific_integration: bool = False


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
class FullStackConvergenceAssessment:
    convergence_state: str
    platform_maturity_state: str
    decoder_state: str
    decoder_capacity_ratio: float
    migration_margin_years: Optional[float]
    urgency: str
    blocking_gaps: tuple[str, ...]

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
    """Assess whether measured QEC evidence can be bridged to an attack estimate."""

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

    projection_state = "MODEL_READY_NOT_PRODUCTION_BREAK" if not gaps else "CROSS_ARCHITECTURE_PROJECTION_BLOCKED"

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
    """Compare a published attack envelope with a forward hardware roadmap."""

    reasons: list[str] = []
    years_to_target = roadmap.target_year - current_year
    logical_headroom = None if roadmap.logical_qubits is None else roadmap.logical_qubits - estimate.logical_qubits
    physical_headroom = None
    if roadmap.physical_qubits is not None and estimate.physical_qubits is not None:
        physical_headroom = roadmap.physical_qubits - estimate.physical_qubits

    logical_collision = logical_headroom is not None and logical_headroom >= 0
    near_logical_collision = logical_headroom is not None and -50 <= logical_headroom < 0
    physical_collision = roadmap.same_architecture_family and physical_headroom is not None and physical_headroom >= 0

    if logical_collision and physical_collision and roadmap.same_architecture_family and estimate.runtime_seconds is not None:
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
    margin = None if migration_years is None else years_to_target - migration_years

    urgency = "MONITOR"
    if collision_state != "NO_COLLISION":
        urgency = "PREPARE_MIGRATION"
        if years_to_target <= 2:
            urgency = "ACCELERATE_MIGRATION_VALIDATION"
        if margin is not None and margin <= 0:
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
        migration_margin_years=margin,
        urgency=urgency,
        reasons=tuple(reasons),
    )


def assess_full_stack_convergence(
    estimate: AttackEstimate,
    roadmap: HardwareRoadmapTarget,
    platform: PlatformMaturityEvidence,
    decoder: ClassicalDecoderEvidence,
    *,
    current_year: int,
    migration_years: Optional[float] = None,
) -> FullStackConvergenceAssessment:
    """Detect convergence across attack, roadmap, platform, QEC and decoder planes.

    This function cannot return a Q2/Q3/Q4 threat level. Its output is a
    migration-planning signal only. In particular, a proposed classical decoder
    or a fabricated prototype QPU is not evidence of a complete cryptanalytic
    machine.
    """

    collision = assess_roadmap_collision(
        estimate,
        roadmap,
        current_year=current_year,
        migration_years=migration_years,
    )
    ratio = decoder.supported_logical_qubits / estimate.logical_qubits
    gaps: list[str] = []

    platform_progress = platform.qpu_fabricated and platform.qubits_trapped_or_operated
    qec_progress = platform.qec_component_validated_on_related_hardware

    if platform.target_scale_demonstrated:
        platform_state = "TARGET_SCALE_DEMONSTRATED"
    elif platform_progress and qec_progress:
        platform_state = "PROTOTYPE_PLATFORM_PLUS_RELATED_QEC_VALIDATED"
    elif platform_progress:
        platform_state = "PROTOTYPE_PLATFORM_DEMONSTRATED"
    else:
        platform_state = "ROADMAP_PLATFORM_ONLY"

    if decoder.demonstrated_hardware and decoder.exact_attack_code_compatible and decoder.attack_specific_integration:
        decoder_state = "ATTACK_INTEGRATED_DECODER_DEMONSTRATED"
    elif decoder.demonstrated_hardware:
        decoder_state = "DECODER_HARDWARE_DEMONSTRATED_NOT_ATTACK_INTEGRATED"
    else:
        decoder_state = "PROPOSED_DECODER_CAPACITY_ONLY"

    roadmap_collision = collision.collision_state == "SAME_ARCHITECTURE_ATTACK_ENVELOPE_COLLISION"
    decoder_near_scale = ratio >= 0.75

    if roadmap_collision and platform_progress and qec_progress and decoder_near_scale:
        convergence_state = "MULTI_PLANE_CONVERGENCE_SIGNAL"
    elif roadmap_collision and (platform_progress or decoder_near_scale):
        convergence_state = "PARTIAL_CONVERGENCE_SIGNAL"
    else:
        convergence_state = "NO_FULL_STACK_CONVERGENCE"

    if not roadmap.demonstrated:
        gaps.append("Attack-scale roadmap target remains forward-looking, not delivered hardware.")
    if not platform.target_scale_demonstrated:
        gaps.append("Prototype/platform evidence does not demonstrate the roadmap's attack-scale qubit count.")
    if not decoder.demonstrated_hardware:
        gaps.append("Decoder capacity is a proposed implementation result, not demonstrated attack-scale hardware.")
    if not decoder.exact_attack_code_compatible:
        gaps.append("Decoder evidence is not validated for the exact QEC code stack used by the attack estimate.")
    if not decoder.attack_specific_integration:
        gaps.append("No end-to-end integration of the decoder with the cryptanalytic workload is demonstrated.")
    gaps.append("Full non-Clifford factory, routing, runtime-reliability and integrated-system scaling remain required unless separately demonstrated.")

    urgency = collision.urgency
    if convergence_state == "MULTI_PLANE_CONVERGENCE_SIGNAL" and urgency == "PREPARE_MIGRATION":
        urgency = "ACCELERATE_MIGRATION_VALIDATION"
    if collision.migration_margin_years is not None and collision.migration_margin_years <= 0:
        urgency = "MIGRATION_SCHEDULE_AT_RISK"

    return FullStackConvergenceAssessment(
        convergence_state=convergence_state,
        platform_maturity_state=platform_state,
        decoder_state=decoder_state,
        decoder_capacity_ratio=ratio,
        migration_margin_years=collision.migration_margin_years,
        urgency=urgency,
        blocking_gaps=tuple(gaps),
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

    Low width, low QEC overhead, roadmaps, prototypes, or proposed decoder scale
    alone can never produce Q2+. Those inputs belong to migration-planning
    convergence analysis, not production-break claims.
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

    if estimate.full_attack and estimate.runtime_seconds is not None and exposure_seconds is not None and exposure_seconds > 0:
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

"""BAROS closed-loop biological adaptation controller.

NON-CLINICAL. RESEARCH ONLY. This module encodes the BAROS operating doctrine:

    measure -> qualify -> propose/re-optimize -> independently recalculate/validate

It does not activate treatment, replace a commissioned TPS, perform patient-
specific QA, or confer clinical authority. When evidence is insufficient,
BAROS holds the last valid research plan identity or falls back to the declared
standard-plan identity instead of forcing adaptation.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class BiologicalState:
    """Voxel-resolved research state at one treatment/adaptation phase."""

    phase_index: int
    alpha_per_gy: tuple[float, ...]
    beta_per_gy2: tuple[float, ...]
    hypoxia_index: tuple[float, ...]
    resistance_index: tuple[float, ...]
    uncertainty: tuple[float, ...]
    anatomy_delta_mm: float = 0.0
    motion_mm: float = 0.0
    measurement_quality: float = 1.0
    geometry_qualified: bool = True
    model_identifiable: bool = True
    out_of_distribution: bool = False

    def validate(self) -> None:
        if self.phase_index < 0:
            raise ValueError("phase_index must be non-negative")
        lengths = {
            len(self.alpha_per_gy),
            len(self.beta_per_gy2),
            len(self.hypoxia_index),
            len(self.resistance_index),
            len(self.uncertainty),
        }
        if len(lengths) != 1 or not self.alpha_per_gy:
            raise ValueError("all voxel-state arrays must have the same non-zero length")

        for name, values in (
            ("alpha_per_gy", self.alpha_per_gy),
            ("beta_per_gy2", self.beta_per_gy2),
            ("hypoxia_index", self.hypoxia_index),
            ("resistance_index", self.resistance_index),
            ("uncertainty", self.uncertainty),
        ):
            if any((not math.isfinite(float(v))) or float(v) < 0.0 for v in values):
                raise ValueError(f"{name} values must be finite and non-negative")

        for name, value in (
            ("anatomy_delta_mm", self.anatomy_delta_mm),
            ("motion_mm", self.motion_mm),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")

        q = float(self.measurement_quality)
        if not math.isfinite(q) or not (0.0 <= q <= 1.0):
            raise ValueError("measurement_quality must be finite and within [0, 1]")


@dataclass(frozen=True)
class AdaptationThresholds:
    """Explicit trigger/qualification thresholds for one locked research use."""

    hypoxia_change: float
    resistance_change: float
    uncertainty_change: float
    anatomy_change_mm: float
    motion_mm: float
    max_uncertainty: float
    min_measurement_quality: float

    def validate(self) -> None:
        for name, value in (
            ("hypoxia_change", self.hypoxia_change),
            ("resistance_change", self.resistance_change),
            ("uncertainty_change", self.uncertainty_change),
            ("anatomy_change_mm", self.anatomy_change_mm),
            ("motion_mm", self.motion_mm),
            ("max_uncertainty", self.max_uncertainty),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        quality = float(self.min_measurement_quality)
        if not math.isfinite(quality) or not (0.0 <= quality <= 1.0):
            raise ValueError("min_measurement_quality must be within [0, 1]")


@dataclass(frozen=True)
class TriggerAssessment:
    triggered: bool
    reasons: tuple[str, ...]
    max_hypoxia_change: float
    max_resistance_change: float
    max_uncertainty_change: float


@dataclass(frozen=True)
class QualificationAssessment:
    qualified: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class AdaptiveDecision:
    action: str
    triggered: bool
    trigger_reasons: tuple[str, ...]
    qualification_blockers: tuple[str, ...]
    proposal_allowed: bool
    treatment_authority: bool
    selected_plan_identity: str
    required_next_steps: tuple[str, ...]


@dataclass(frozen=True)
class PhaseCoupledScore:
    base_loss: float
    uncertainty_penalty: float
    temporal_coupling_penalty: float
    total_score: float


def _max_abs_delta(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("state arrays must have the same non-zero length")
    return max(abs(float(x) - float(y)) for x, y in zip(a, b))


def assess_triggers(
    previous: BiologicalState,
    current: BiologicalState,
    thresholds: AdaptationThresholds,
    *,
    manual_force: bool = False,
) -> TriggerAssessment:
    """Evaluate explicit anatomy/biology/uncertainty/motion adaptation triggers."""
    previous.validate()
    current.validate()
    thresholds.validate()
    if current.phase_index <= previous.phase_index:
        raise ValueError("current phase_index must be greater than previous phase_index")
    if len(previous.alpha_per_gy) != len(current.alpha_per_gy):
        raise ValueError("voxel-state dimensionality changed without an explicit mapping")

    hypoxia_delta = _max_abs_delta(previous.hypoxia_index, current.hypoxia_index)
    resistance_delta = _max_abs_delta(previous.resistance_index, current.resistance_index)
    uncertainty_delta = _max_abs_delta(previous.uncertainty, current.uncertainty)

    reasons: list[str] = []
    if manual_force:
        reasons.append("manual_force")
    if hypoxia_delta >= thresholds.hypoxia_change:
        reasons.append("hypoxia_change")
    if resistance_delta >= thresholds.resistance_change:
        reasons.append("resistance_change")
    if uncertainty_delta >= thresholds.uncertainty_change:
        reasons.append("uncertainty_change")
    if current.anatomy_delta_mm >= thresholds.anatomy_change_mm:
        reasons.append("anatomy_change")
    if current.motion_mm >= thresholds.motion_mm:
        reasons.append("motion")

    return TriggerAssessment(
        triggered=bool(reasons),
        reasons=tuple(reasons),
        max_hypoxia_change=hypoxia_delta,
        max_resistance_change=resistance_delta,
        max_uncertainty_change=uncertainty_delta,
    )


def qualify_state(
    state: BiologicalState,
    thresholds: AdaptationThresholds,
) -> QualificationAssessment:
    """Fail closed when the measured state is not trustworthy enough to adapt."""
    state.validate()
    thresholds.validate()
    blockers: list[str] = []

    if not state.geometry_qualified:
        blockers.append("geometry_not_qualified")
    if not state.model_identifiable:
        blockers.append("model_not_identifiable")
    if state.out_of_distribution:
        blockers.append("out_of_distribution")
    if state.measurement_quality < thresholds.min_measurement_quality:
        blockers.append("measurement_quality_below_threshold")
    if max(state.uncertainty) > thresholds.max_uncertainty:
        blockers.append("uncertainty_above_threshold")

    return QualificationAssessment(
        qualified=not blockers,
        blockers=tuple(blockers),
    )


def phase_coupled_score(
    phase_losses: Sequence[float],
    control_vectors: Sequence[Sequence[float]],
    phase_uncertainty: Sequence[float],
    *,
    uncertainty_weight: float,
    temporal_coupling_weight: float,
) -> PhaseCoupledScore:
    """Bounded generic phase-coupled objective.

    This does not prescribe a clinical biological model. Callers provide the
    per-phase loss values. BAROS adds explicit uncertainty and temporal control
    discontinuity penalties so adaptation cannot optimize each phase as though
    neighboring phases were unrelated.
    """
    losses = [float(v) for v in phase_losses]
    uncertainty = [float(v) for v in phase_uncertainty]
    controls = [[float(v) for v in row] for row in control_vectors]

    if not losses or len(losses) != len(controls) or len(losses) != len(uncertainty):
        raise ValueError("phase losses, controls, and uncertainty must have the same non-zero length")
    if any(not math.isfinite(v) for v in losses):
        raise ValueError("phase losses must be finite")
    if any((not math.isfinite(v)) or v < 0.0 for v in uncertainty):
        raise ValueError("phase uncertainty must be finite and non-negative")
    if not controls[0]:
        raise ValueError("control vectors must be non-empty")
    width = len(controls[0])
    if any(len(row) != width for row in controls):
        raise ValueError("all control vectors must have equal dimensionality")
    if any(not math.isfinite(v) for row in controls for v in row):
        raise ValueError("control vectors must be finite")

    uw = float(uncertainty_weight)
    tw = float(temporal_coupling_weight)
    if not math.isfinite(uw) or uw < 0.0:
        raise ValueError("uncertainty_weight must be finite and non-negative")
    if not math.isfinite(tw) or tw < 0.0:
        raise ValueError("temporal_coupling_weight must be finite and non-negative")

    base = sum(losses)
    uncertainty_penalty = uw * sum(uncertainty)
    coupling = 0.0
    for previous, current in zip(controls, controls[1:]):
        coupling += sum((c - p) ** 2 for p, c in zip(previous, current))
    coupling *= tw

    return PhaseCoupledScore(
        base_loss=base,
        uncertainty_penalty=uncertainty_penalty,
        temporal_coupling_penalty=coupling,
        total_score=base + uncertainty_penalty + coupling,
    )


def decide_adaptation(
    *,
    previous: BiologicalState,
    current: BiologicalState,
    thresholds: AdaptationThresholds,
    last_valid_plan_identity: str | None,
    standard_plan_identity: str,
    manual_force: bool = False,
) -> AdaptiveDecision:
    """Run the measure->qualify decision boundary before any re-optimization.

    A qualified trigger permits only a research proposal. The result still
    requires external TPS/dose-engine recalculation, protocol-defined QA, and
    authorized human review. This function never grants treatment authority.
    """
    if not standard_plan_identity.strip():
        raise ValueError("standard_plan_identity must be non-empty")
    if last_valid_plan_identity is not None and not last_valid_plan_identity.strip():
        raise ValueError("last_valid_plan_identity must be non-empty when supplied")

    trigger = assess_triggers(previous, current, thresholds, manual_force=manual_force)
    qualification = qualify_state(current, thresholds)
    safe_plan = last_valid_plan_identity or standard_plan_identity

    if not trigger.triggered:
        return AdaptiveDecision(
            action="NO_ADAPTATION",
            triggered=False,
            trigger_reasons=(),
            qualification_blockers=qualification.blockers,
            proposal_allowed=False,
            treatment_authority=False,
            selected_plan_identity=safe_plan,
            required_next_steps=("continue governed monitoring",),
        )

    if not qualification.qualified:
        action = "HOLD_LAST_VALID" if last_valid_plan_identity else "FALLBACK_STANDARD"
        return AdaptiveDecision(
            action=action,
            triggered=True,
            trigger_reasons=trigger.reasons,
            qualification_blockers=qualification.blockers,
            proposal_allowed=False,
            treatment_authority=False,
            selected_plan_identity=safe_plan,
            required_next_steps=(
                "resolve qualification blockers",
                "preserve current authoritative plan",
                "do not re-optimize from unqualified biological state",
            ),
        )

    return AdaptiveDecision(
        action="PROPOSE_REOPTIMIZATION",
        triggered=True,
        trigger_reasons=trigger.reasons,
        qualification_blockers=(),
        proposal_allowed=True,
        treatment_authority=False,
        selected_plan_identity=safe_plan,
        required_next_steps=(
            "generate bounded BAROS candidate",
            "independent TPS or approved dose-engine recalculation",
            "protocol-defined dosimetric and deliverability validation",
            "qualified human review/authorization",
            "retain last valid or standard plan until all external gates pass",
        ),
    )

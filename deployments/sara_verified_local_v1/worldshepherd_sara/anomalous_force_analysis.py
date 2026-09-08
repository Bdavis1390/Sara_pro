from __future__ import annotations

from enum import Enum
from math import isfinite
from typing import Any

from pydantic import BaseModel, Field, model_validator

C_M_PER_S = 299_792_458.0


class GateState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    OPEN = "OPEN"


class AnomalousForceEvidenceSummary(BaseModel):
    """Bounded summary for AF-0 through AF-7 screening.

    This model is intentionally conservative. It accepts already-derived force and
    uncertainty summaries plus explicit gate states; it does not replace raw-data
    analysis, uncertainty estimation, calibration, or independent scientific review.
    """

    campaign_id: str = Field(min_length=1, max_length=256)
    article_id: str = Field(min_length=1, max_length=256)
    preregistered: bool
    input_power_w: float = Field(gt=0)
    photon_baseline_power_w: float | None = Field(default=None, gt=0)
    measured_force_n: float
    expanded_uncertainty_n: float = Field(ge=0)
    known_momentum_force_bound_n: float = Field(ge=0)
    af0_instrument_competence: GateState
    af1_null_control_separation: GateState
    af2_directionality: GateState
    af3_confounder_closure: GateState
    af4_scaling_law: GateState
    af5_internal_replication: GateState
    af6_instrument_independence: GateState
    af7_external_replication: GateState
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "AnomalousForceEvidenceSummary":
        for name, value in {
            "input_power_w": self.input_power_w,
            "measured_force_n": self.measured_force_n,
            "expanded_uncertainty_n": self.expanded_uncertainty_n,
            "known_momentum_force_bound_n": self.known_momentum_force_bound_n,
        }.items():
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.photon_baseline_power_w is not None and not isfinite(
            self.photon_baseline_power_w
        ):
            raise ValueError("photon_baseline_power_w must be finite")
        return self


def _gate_map(summary: AnomalousForceEvidenceSummary) -> dict[str, str]:
    return {
        "AF-0": summary.af0_instrument_competence.value,
        "AF-1": summary.af1_null_control_separation.value,
        "AF-2": summary.af2_directionality.value,
        "AF-3": summary.af3_confounder_closure.value,
        "AF-4": summary.af4_scaling_law.value,
        "AF-5": summary.af5_internal_replication.value,
        "AF-6": summary.af6_instrument_independence.value,
        "AF-7": summary.af7_external_replication.value,
    }


def assess_anomalous_force_summary(
    summary: AnomalousForceEvidenceSummary,
) -> dict[str, Any]:
    """Return a falsification-first screening result.

    A high force/photon ratio is never interpreted here as proof of reactionless,
    electrogravitic, gravity-control, or other beyond-standard-model propulsion.
    """

    photon_power_w = summary.photon_baseline_power_w or summary.input_power_w
    photon_force_n = photon_power_w / C_M_PER_S
    absolute_force_n = abs(summary.measured_force_n)
    photon_ratio_abs = absolute_force_n / photon_force_n
    explained_plus_uncertainty_n = (
        summary.known_momentum_force_bound_n + summary.expanded_uncertainty_n
    )
    conservative_residual_lower_bound_n = max(
        absolute_force_n - explained_plus_uncertainty_n,
        0.0,
    )

    gates = _gate_map(summary)
    failed = sorted(name for name, state in gates.items() if state == GateState.FAIL.value)
    open_gates = sorted(name for name, state in gates.items() if state == GateState.OPEN.value)

    if conservative_residual_lower_bound_n <= 0:
        classification = "NO_UNEXPLAINED_RESIDUAL"
    elif summary.af0_instrument_competence != GateState.PASS:
        classification = "NULL_OR_UNRESOLVED"
    elif summary.af1_null_control_separation != GateState.PASS:
        classification = "NULL_OR_UNRESOLVED"
    elif summary.af2_directionality != GateState.PASS:
        classification = "UNRESOLVED_RESIDUAL"
    elif summary.af3_confounder_closure != GateState.PASS:
        classification = "UNRESOLVED_RESIDUAL"
    elif not summary.preregistered:
        classification = "EXPLORATORY_RESIDUAL"
    elif summary.af4_scaling_law != GateState.PASS:
        classification = "UNRESOLVED_RESIDUAL"
    elif summary.af5_internal_replication != GateState.PASS:
        classification = "UNRESOLVED_RESIDUAL"
    elif summary.af6_instrument_independence != GateState.PASS:
        classification = "ANOMALY_CANDIDATE"
    elif summary.af7_external_replication != GateState.PASS:
        classification = "INDEPENDENT_REPLICATION_REQUIRED"
    else:
        classification = "INDEPENDENTLY_REPLICATED_BOUNDED_EFFECT"

    bounded_effect_claim_candidate = (
        classification == "INDEPENDENTLY_REPLICATED_BOUNDED_EFFECT"
    )

    return {
        "campaign_id": summary.campaign_id,
        "article_id": summary.article_id,
        "photon_force_n": photon_force_n,
        "photon_ratio_abs": photon_ratio_abs,
        "absolute_measured_force_n": absolute_force_n,
        "expanded_uncertainty_n": summary.expanded_uncertainty_n,
        "known_momentum_force_bound_n": summary.known_momentum_force_bound_n,
        "conservative_residual_lower_bound_n": conservative_residual_lower_bound_n,
        "gates": gates,
        "failed_gates": failed,
        "open_gates": open_gates,
        "classification": classification,
        "bounded_effect_claim_candidate": bounded_effect_claim_candidate,
        "reactionless_claim_allowed": False,
        "electrogravitic_claim_allowed": False,
        "gravity_control_claim_allowed": False,
        "new_physics_confirmed": False,
        "status_note": (
            "An independently replicated bounded force effect may be described only within the frozen apparatus/configuration and uncertainty boundary; physical interpretation remains a separate scientific question."
            if bounded_effect_claim_candidate
            else "Result remains below the independent bounded-effect threshold and cannot support extraordinary propulsion or new-physics wording."
        ),
    }

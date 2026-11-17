"""Transparent research-only biological-to-objective-intent mapping.

This module illustrates the EXACT boundary requested for scientific review:
qualified longitudinal synthetic signal -> explicit *abstract* priority change.
It is NOT a clinical model, TPS optimizer or DICOM RTPLAN interface.
Gain, cap, input indices and thresholds are investigator-unvalidated toy choices.
No radiation dose, fractionation, target/OAR weights in a commissioned TPS,
prescription, delivery parameter or patient-care authority is produced.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .closed_loop import AdaptationThresholds, BiologicalState, decide_adaptation


_REGION_RE = re.compile(r"^SYN-[A-Z0-9_-]{1,20}$")


@dataclass(frozen=True)
class ResearchPriorityPolicy:
    """Arbitrary synthetic relative weighting only; no clinical units."""

    gain_per_index_unit: float
    max_abstract_priority_delta: float

    def validate(self) -> None:
        for name, x in (
            ("gain_per_index_unit", self.gain_per_index_unit),
            ("max_abstract_priority_delta", self.max_abstract_priority_delta),
        ):
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise ValueError(f"{name} must be a finite research-only scalar")
            if not math.isfinite(float(x)) or not 0.0 <= x <= 1.0:
                raise ValueError(f"{name} must be within [0,1]")


@dataclass(frozen=True)
class AbstractRegionPriority:
    region_id: str
    positive_hypoxia_index_delta: float
    abstract_priority_delta: float


@dataclass(frozen=True)
class ResearchObjectiveIntent:
    intended_use: str
    decision_action: str
    synthetic_policy_only: bool
    proposal_allowed: bool
    treatment_authority: bool
    dose_or_prescription_defined: bool
    tps_export_allowed: bool
    region_priorities: tuple[AbstractRegionPriority, ...]
    next_step: str


def make_synthetic_research_objective_intent(
    *,
    previous: BiologicalState,
    current: BiologicalState,
    thresholds: AdaptationThresholds,
    policy: ResearchPriorityPolicy,
    region_ids: tuple[str, ...],
    last_valid_plan_identity: str | None = "SYNTHETIC-LAST-PLAN",
    standard_plan_identity: str = "SYNTHETIC-STANDARD-PLAN",
) -> ResearchObjectiveIntent:
    """Evaluate BAROS evidence gates before any abstract objective mapping.

    This function accepts only synthetic region IDs (SYN-...), which do not
    identify clinical structures. The output is an *explanation of proposed
    research priorities*, not a TPS-compatible objective list.
    """
    policy.validate()
    if not isinstance(region_ids, tuple):
        raise ValueError("region_ids must be a fixed tuple")
    if len(region_ids) != len(current.hypoxia_index) or not region_ids:
        raise ValueError("one synthetic region identifier is required per state entry")
    if any(not isinstance(s, str) or _REGION_RE.fullmatch(s) is None for s in region_ids):
        raise ValueError("region identifiers must be synthetic SYN- tokens only")
    if len(set(region_ids)) != len(region_ids):
        raise ValueError("synthetic region identifiers must be unique")

    decision = decide_adaptation(
        previous=previous,
        current=current,
        thresholds=thresholds,
        last_valid_plan_identity=last_valid_plan_identity,
        standard_plan_identity=standard_plan_identity,
        manual_force=False,
    )
    priorities: list[AbstractRegionPriority] = []
    # A qualified *biological* signal is mandatory for an abstract priority
    # change. Geometry/motion-only research proposals do not imply biologic
    # upweighting, nor does a decreasing hypoxia index automatically imply
    # an increase or decrease in prescribed dose.
    if decision.proposal_allowed and "hypoxia_change" in decision.trigger_reasons:
        for region, prior, observed in zip(
            region_ids, previous.hypoxia_index, current.hypoxia_index
        ):
            positive = max(0.0, float(observed) - float(prior))
            priority = min(
                policy.max_abstract_priority_delta,
                positive * policy.gain_per_index_unit,
            )
            priorities.append(AbstractRegionPriority(region, positive, priority))

    return ResearchObjectiveIntent(
        intended_use="SYNTHETIC_PRE_TPS_OBJECTIVE_REVIEW_ONLY",
        decision_action=decision.action,
        synthetic_policy_only=True,
        proposal_allowed=decision.proposal_allowed,
        treatment_authority=False,
        dose_or_prescription_defined=False,
        tps_export_allowed=False,
        region_priorities=tuple(priorities),
        next_step=(
            "external investigator must define clinical relevance, validate "
            "biomarker and TPS objective semantics; do NOT generate or deliver "
            "radiotherapy from these abstract values"
        ),
    )

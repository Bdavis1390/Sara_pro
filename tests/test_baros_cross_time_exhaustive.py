"""Exhaustive synthetic cross-time qualification invariant for BAROS.

One pytest regression evaluates all 32 x 32 prior/current flag combinations.
These are developer-authored software cases, NOT clinical samples or independent
medical ground truth. The test provides no statistical claim of safety.
"""

from dataclasses import replace
from itertools import product

from baros.closed_loop import AdaptationThresholds, BiologicalState, decide_adaptation


LIMITS = AdaptationThresholds(
    hypoxia_change=0.10,
    resistance_change=0.10,
    uncertainty_change=0.10,
    anatomy_change_mm=3.0,
    motion_mm=4.0,
    max_uncertainty=0.20,
    min_measurement_quality=0.80,
)


def _state(phase: int, *, changed: bool):
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.45) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=0.95,
        geometry_qualified=True,
        model_identifiable=True,
        out_of_distribution=False,
    )


def _with_flags(state, flags):
    geometry, identifiable, ood, good_quality, acceptable_uncertainty = flags
    return replace(
        state,
        geometry_qualified=geometry,
        model_identifiable=identifiable,
        out_of_distribution=ood,
        measurement_quality=0.95 if good_quality else 0.50,
        uncertainty=(0.05, 0.05) if acceptable_uncertainty else (0.05, 0.35),
    )


def _qualified(flags):
    geometry, identifiable, ood, good_quality, acceptable_uncertainty = flags
    return geometry and identifiable and not ood and good_quality and acceptable_uncertainty


def test_all_1024_cross_time_qualification_combinations_fail_closed():
    flags = tuple(product(
        (False, True), (False, True), (False, True),
        (False, True), (False, True),
    ))
    seen = allowed = blocked = 0
    for prior_flags in flags:
        for current_flags in flags:
            prior = _with_flags(_state(0, changed=False), prior_flags)
            current = _with_flags(_state(1, changed=True), current_flags)
            decision = decide_adaptation(
                previous=prior,
                current=current,
                thresholds=LIMITS,
                last_valid_plan_identity="RESEARCH-LAST-VALID",
                standard_plan_identity="RESEARCH-STANDARD",
            )
            expected = bool(_qualified(prior_flags) and _qualified(current_flags))
            assert decision.triggered
            assert decision.proposal_allowed is expected
            assert decision.treatment_authority is False
            assert decision.selected_plan_identity == "RESEARCH-LAST-VALID"
            assert decision.action == (
                "PROPOSE_REOPTIMIZATION" if expected else "HOLD_LAST_VALID"
            )
            seen += 1
            allowed += int(decision.proposal_allowed)
            blocked += int(not decision.proposal_allowed)
    # Only the one fully-qualified prior/current pair is allowed.
    assert (seen, allowed, blocked) == (1024, 1, 1023)

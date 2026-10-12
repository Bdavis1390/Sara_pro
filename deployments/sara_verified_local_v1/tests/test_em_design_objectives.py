from worldshepherd_sara.em_design_objectives import (
    EMDesignCandidate,
    EMDesignMetrics,
    design_objective_contract,
    dominates,
    pareto_front,
)


def _candidate(candidate_id: str, **values: float) -> EMDesignCandidate:
    defaults = {
        "te_angle_observability": 100.0,
        "tm_phase_span_deg": 80.0,
        "polarization_isolation_dB": 60.0,
        "minimum_reflection_magnitude": 0.90,
        "te_state_crosstalk": 0.01,
        "tm_refinement_uncertainty": 0.10,
        "tm_oblique_refinement_uncertainty": 0.15,
        "loss_proxy": 0.05,
    }
    defaults.update(values)
    return EMDesignCandidate(
        candidate_id=candidate_id,
        design_version="test",
        metrics=EMDesignMetrics(**defaults),
    )


def test_strictly_better_candidate_dominates():
    base = _candidate("BASE")
    better = _candidate(
        "BETTER",
        tm_phase_span_deg=100.0,
        tm_refinement_uncertainty=0.08,
        tm_oblique_refinement_uncertainty=0.12,
    )
    assert dominates(better, base) is True
    assert dominates(base, better) is False


def test_tradeoff_candidates_are_both_pareto_optimal():
    angle_focused = _candidate(
        "ANGLE",
        te_angle_observability=150.0,
        tm_phase_span_deg=70.0,
    )
    phase_focused = _candidate(
        "PHASE",
        te_angle_observability=90.0,
        tm_phase_span_deg=140.0,
    )
    front = pareto_front([phase_focused, angle_focused])
    assert [item.candidate_id for item in front] == ["ANGLE", "PHASE"]


def test_oblique_stability_tradeoff_cannot_be_hidden_by_phase_gain():
    stable = _candidate(
        "STABLE",
        tm_phase_span_deg=80.0,
        tm_oblique_refinement_uncertainty=0.05,
    )
    wider_phase_but_unstable = _candidate(
        "WIDE_PHASE",
        tm_phase_span_deg=160.0,
        tm_oblique_refinement_uncertainty=0.30,
    )
    front = pareto_front([stable, wider_phase_but_unstable])
    assert [item.candidate_id for item in front] == ["STABLE", "WIDE_PHASE"]


def test_dominated_candidate_is_removed_from_front():
    base = _candidate("BASE")
    worse = _candidate(
        "WORSE",
        te_angle_observability=90.0,
        tm_phase_span_deg=70.0,
        polarization_isolation_dB=55.0,
        minimum_reflection_magnitude=0.85,
        te_state_crosstalk=0.02,
        tm_refinement_uncertainty=0.12,
        tm_oblique_refinement_uncertainty=0.18,
        loss_proxy=0.06,
    )
    front = pareto_front([worse, base])
    assert [item.candidate_id for item in front] == ["BASE"]


def test_contract_forbids_scalar_weighted_score_and_validation_claim():
    contract = design_objective_contract()
    assert contract["scalar_weighted_score"] is False
    assert contract["selection_method"] == "PARETO_NON_DOMINANCE"
    assert "tm_oblique_refinement_uncertainty" in contract["minimize"]
    assert "OBLIQUE_STABILITY_IS_A_NEXTGEN_OBJECTIVE_NOT_A_UC06_GATE" in contract["claims_boundary"]
    assert "NO_NEW_UC06_ACCEPTANCE_THRESHOLD" in contract["claims_boundary"]
    assert "NO_CANDIDATE_VALIDATED_BY_PARETO_STATUS" in contract["claims_boundary"]

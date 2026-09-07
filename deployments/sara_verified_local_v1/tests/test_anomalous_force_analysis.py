from __future__ import annotations

import pytest

from worldshepherd_sara.anomalous_force_analysis import (
    AnomalousForceEvidenceSummary,
    GateState,
    assess_anomalous_force_summary,
)


def _summary(**overrides):
    payload = {
        "campaign_id": "AFEM-TEST-001",
        "article_id": "ARTICLE-001",
        "preregistered": True,
        "input_power_w": 1000.0,
        "measured_force_n": 50e-6,
        "expanded_uncertainty_n": 2e-6,
        "known_momentum_force_bound_n": 3e-6,
        "af0_instrument_competence": GateState.PASS,
        "af1_null_control_separation": GateState.PASS,
        "af2_directionality": GateState.PASS,
        "af3_confounder_closure": GateState.PASS,
        "af4_scaling_law": GateState.PASS,
        "af5_internal_replication": GateState.PASS,
        "af6_instrument_independence": GateState.OPEN,
        "af7_external_replication": GateState.OPEN,
    }
    payload.update(overrides)
    return AnomalousForceEvidenceSummary(**payload)


def test_photon_baseline_is_computed_but_not_interpreted_as_new_physics():
    result = assess_anomalous_force_summary(_summary())
    assert result["photon_force_n"] == pytest.approx(1000.0 / 299_792_458.0)
    assert result["photon_ratio_abs"] > 1.0
    assert result["classification"] == "ANOMALY_CANDIDATE"
    assert result["reactionless_claim_allowed"] is False
    assert result["electrogravitic_claim_allowed"] is False
    assert result["new_physics_confirmed"] is False


def test_force_inside_uncertainty_and_known_budget_has_no_unexplained_residual():
    result = assess_anomalous_force_summary(
        _summary(
            measured_force_n=4e-6,
            expanded_uncertainty_n=2e-6,
            known_momentum_force_bound_n=3e-6,
        )
    )
    assert result["conservative_residual_lower_bound_n"] == 0.0
    assert result["classification"] == "NO_UNEXPLAINED_RESIDUAL"


def test_open_confounder_gate_blocks_anomaly_candidate():
    result = assess_anomalous_force_summary(
        _summary(af3_confounder_closure=GateState.OPEN)
    )
    assert result["classification"] == "UNRESOLVED_RESIDUAL"
    assert "AF-3" in result["open_gates"]


def test_unpreregistered_result_remains_exploratory():
    result = assess_anomalous_force_summary(
        _summary(
            preregistered=False,
            af6_instrument_independence=GateState.PASS,
            af7_external_replication=GateState.PASS,
        )
    )
    assert result["classification"] == "EXPLORATORY_RESIDUAL"
    assert result["bounded_effect_claim_candidate"] is False


def test_instrument_independence_advances_only_to_external_replication_required():
    result = assess_anomalous_force_summary(
        _summary(af6_instrument_independence=GateState.PASS)
    )
    assert result["classification"] == "INDEPENDENT_REPLICATION_REQUIRED"
    assert result["new_physics_confirmed"] is False


def test_external_replication_allows_only_bounded_effect_candidate():
    result = assess_anomalous_force_summary(
        _summary(
            af6_instrument_independence=GateState.PASS,
            af7_external_replication=GateState.PASS,
        )
    )
    assert result["classification"] == "INDEPENDENTLY_REPLICATED_BOUNDED_EFFECT"
    assert result["bounded_effect_claim_candidate"] is True
    assert result["reactionless_claim_allowed"] is False
    assert result["gravity_control_claim_allowed"] is False
    assert result["new_physics_confirmed"] is False

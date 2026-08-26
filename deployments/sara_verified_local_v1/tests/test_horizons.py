from __future__ import annotations

import pytest

from worldshepherd_sara.horizons import CapabilityHorizonPortfolio, CapabilityHorizonRecord
from worldshepherd_sara.qualification import ForecastHorizon
from worldshepherd_sara.readiness import ReadinessRung


def test_horizon_portfolio_keeps_forecast_actions_separate_from_readiness_claims():
    portfolio = CapabilityHorizonPortfolio(records=[
        CapabilityHorizonRecord(
            horizon_id="H-APNT-001",
            capability_id="CAP-APNT",
            horizon=ForecastHorizon.D0_90,
            prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE,
            target_rung=ReadinessRung.SIMULATION,
            requirement_delta_ids=["PRE-RD-2026-0001"],
            build_actions=["implement authoritative ASPN mapping adapter"],
            experiments=["run representative simulation with controlled source faults"],
            partner_actions=["obtain APNT interface/validation partner"],
            evidence_targets=["simulation qualification bundle"],
            blocking_conditions=["authoritative interface definitions unavailable"],
            forecast_only=True,
        )
    ])
    assert portfolio.records[0].forecast_only is True
    assert "implement authoritative ASPN mapping adapter" in portfolio.immediate_actions()


def test_horizon_record_rejects_multi_rung_readiness_jump():
    with pytest.raises(ValueError):
        CapabilityHorizonRecord(
            horizon_id="H-BAD",
            capability_id="CAP-BAD",
            horizon=ForecastHorizon.D0_90,
            prerequisite_rung=ReadinessRung.INTERNAL_SOFTWARE,
            target_rung=ReadinessRung.PHYSICAL_LAB,
        )

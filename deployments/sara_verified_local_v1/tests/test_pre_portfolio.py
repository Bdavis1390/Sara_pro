from __future__ import annotations

from worldshepherd_sara.pre_portfolio import build_horizon_portfolio, build_readiness_ledger


def test_readiness_ledger_separates_synthetic_software_from_rf_simulation_rung():
    digests = {name: "sha256:" + str(index) * 64 for index, name in enumerate(["apnt","mbse","ietm","ade","mission","fusion","cbm","manufacturing","ddil","rf"], start=1)}
    ledger = build_readiness_ledger(digests)
    records = {record["capability_id"]: record for record in ledger["records"]}
    assert records["CAP-APNT"]["highest_supported_rung"] == 3
    assert records["CAP-RF-DISCREPANCY"]["highest_supported_rung"] == 4
    assert records["CAP-RF-DISCREPANCY"]["blocked_next_rung"] == 5
    assert ledger["ledger_digest"].startswith("sha256:")


def test_horizon_portfolio_covers_all_three_windows_and_is_forecast_only():
    portfolio = build_horizon_portfolio()
    horizons = {record["horizon"] for record in portfolio["records"]}
    assert {"0-90D", "3-12M", "12-24M_PLUS"}.issubset(horizons)
    assert all(record["forecast_only"] is True for record in portfolio["records"])
    assert portfolio["immediate_actions"]
    assert portfolio["portfolio_digest"].startswith("sha256:")

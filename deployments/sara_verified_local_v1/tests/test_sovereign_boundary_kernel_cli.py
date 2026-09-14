from __future__ import annotations

from worldshepherd_sara.sovereign_boundary_kernel_cli import run_demo


def test_sovereign_boundary_demo_completes_and_blocks_physical_promotion():
    result = run_demo(scenario_id="coherent_target")
    assert result["benchmark_capability_status"] == "SIMULATED_ONLY"
    assert result["terminal_state"] == "EXECUTED"
    assert result["envelope_verified"] is True
    assert result["physical_promotion_blocked"] is True
    assert result["action_digest"].startswith("sha256:")
    assert result["envelope_digest"].startswith("sha256:")

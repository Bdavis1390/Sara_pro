from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.rmabm_faults import build_seeded_fault_plan, run_seeded_fault_campaign

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures" / "rmabm_g1_synthetic_v1.json").read_text())


def test_seeded_fault_plan_is_reproducible():
    fixture = _fixture()
    first = build_seeded_fault_plan(fixture, seed=9675)
    second = build_seeded_fault_plan(fixture, seed=9675)
    assert first == second


def test_seeded_fault_campaign_preserves_safety_boundary():
    results = run_seeded_fault_campaign(_fixture(), seed=9675)
    assert len(results) == 6
    assert all(result.boundary_integrity for result in results)

    blocked = next(result for result in results if result.kind == "request_blocked_action")
    assert blocked.accepted is True
    assert blocked.authorized_advisory_count == 0
    assert blocked.block_count > 0

    no_human = next(result for result in results if result.kind == "remove_human_authority")
    assert no_human.accepted is True
    assert no_human.authorized_advisory_count == 0
    assert no_human.hold_count > 0


def test_duplicate_observation_id_is_rejected_before_fusion():
    results = run_seeded_fault_campaign(_fixture(), seed=9675)
    duplicate = next(result for result in results if result.kind == "duplicate_observation_id")
    assert duplicate.accepted is False
    assert duplicate.rejected_reason is not None
    assert "duplicate observation ids rejected" in duplicate.rejected_reason
    assert duplicate.authorized_advisory_count == 0


def test_delay_fault_is_traceable_when_it_makes_source_stale():
    fixture = _fixture()
    plan = build_seeded_fault_plan(fixture, seed=9675)
    delay = next(item for item in plan if item.kind == "delay_observation")
    results = run_seeded_fault_campaign(fixture, seed=9675)
    delayed_result = next(item for item in results if item.fault_id == delay.fault_id)
    assert delayed_result.accepted is True
    assert delay.target_observation_id in delayed_result.stale_observation_ids


def test_campaign_replay_is_reproducible_for_same_seed():
    first = run_seeded_fault_campaign(_fixture(), seed=9675)
    second = run_seeded_fault_campaign(_fixture(), seed=9675)
    assert first == second

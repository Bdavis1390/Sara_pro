from __future__ import annotations

import copy
import json
from pathlib import Path

from worldshepherd_sara.rmabm import CLAIMS_BOUNDARY, run_synthetic_rmabm

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict:
    return json.loads((ROOT / "fixtures" / "rmabm_g1_synthetic_v1.json").read_text())


def test_rmabm_g1_authorizes_only_bounded_advisory_and_holds_weak_track():
    fixture = _fixture()
    result = run_synthetic_rmabm(fixture)

    assert result.evidence_state == "IMPLEMENTED_IN_SOFTWARE_SYNTHETIC_ONLY"
    assert result.claims_boundary == CLAIMS_BOUNDARY
    assert result.ordered_event_sequences == fixture["expected"]["ordered_event_sequences"]
    assert result.stale_observation_ids == fixture["expected"]["stale_observation_ids"]

    authorized = [decision for decision in result.decisions if decision.decision == "AUTHORIZED_ADVISORY"]
    held = [decision for decision in result.decisions if decision.decision == "HOLD"]
    assert len(authorized) == fixture["expected"]["authorized_advisory_count"]
    assert len(held) == fixture["expected"]["hold_count"]
    assert all(decision.requested_action == "advisory_dissemination" for decision in result.decisions)

    assert result.metrics.provenance_completeness == fixture["expected"]["provenance_completeness"]
    assert result.metrics.policy_enforcement_rate == fixture["expected"]["policy_enforcement_rate"]
    assert result.metrics.stale_observation_traceability == fixture["expected"]["stale_observation_traceability"]
    assert result.metrics.degraded_state_continuity is fixture["expected"]["degraded_state_continuity"]


def test_rmabm_g1_blocks_fire_control_or_engagement_output():
    fixture = _fixture()
    fixture["requested_action"] = "fire_control_cue"
    result = run_synthetic_rmabm(fixture)

    assert result.decisions
    assert all(decision.decision == "BLOCK" for decision in result.decisions)
    assert all("prohibits fire-control" in decision.reasons[0] for decision in result.decisions)
    assert result.metrics.policy_enforcement_rate == 1.0


def test_rmabm_g1_requires_human_authority_for_advisory_release():
    fixture = _fixture()
    fixture["human_authority"] = None
    result = run_synthetic_rmabm(fixture)

    assert result.decisions
    assert all(decision.decision == "HOLD" for decision in result.decisions)
    assert any(
        "identified human authority" in reason
        for decision in result.decisions
        for reason in decision.reasons
    )


def test_rmabm_g1_is_deterministic_for_same_fixture():
    fixture = _fixture()
    first = run_synthetic_rmabm(copy.deepcopy(fixture))
    second = run_synthetic_rmabm(copy.deepcopy(fixture))

    assert first.metrics.deterministic_replay_digest == second.metrics.deterministic_replay_digest
    assert first.audit_sha256 == second.audit_sha256


def test_rmabm_g1_rejects_unknown_consequential_action():
    fixture = _fixture()
    fixture["requested_action"] = "autonomous_consequential_action"

    try:
        run_synthetic_rmabm(fixture)
    except ValueError as exc:
        assert "permits only" in str(exc)
    else:
        raise AssertionError("unknown consequential action should be rejected")

from __future__ import annotations

import pytest

from worldshepherd_sara.cbm_twin import HealthFinding
from worldshepherd_sara.prime import ActionState
from worldshepherd_sara.release_health_gate import ReleaseGate, evaluate_release_gate


def _finding(status: str) -> HealthFinding:
    return HealthFinding(
        sample_id="S1",
        asset_id="service-1",
        metric="temperature_c",
        status=status,
        deviation=0.0 if status == "NOMINAL" else 5.0,
        expected_minimum=10.0,
        expected_maximum=40.0,
    )


def test_nominal_health_requires_reviewer_and_allows_reviewed_release():
    decision = evaluate_release_gate(
        (_finding("NOMINAL"),),
        reviewer="REVIEWER-1",
        release_requested=True,
    )

    assert decision.readiness == "READY"
    assert decision.gate == ReleaseGate.APPLIED
    assert decision.release_allowed is True
    assert decision.authorization_state == ActionState.APPROVED


def test_degraded_health_blocks_ordinary_release():
    decision = evaluate_release_gate(
        (_finding("HIGH"),),
        reviewer="REVIEWER-1",
        release_requested=True,
    )

    assert decision.readiness == "DEGRADED"
    assert decision.gate == ReleaseGate.DENIED
    assert decision.release_allowed is False
    assert decision.authorization_state == ActionState.DENIED


def test_degraded_health_requires_separately_explicit_exception():
    decision = evaluate_release_gate(
        (_finding("HIGH"),),
        reviewer="REVIEWER-1",
        release_requested=True,
        explicit_degraded_override=True,
    )

    assert decision.gate == ReleaseGate.OVERRIDDEN
    assert decision.release_allowed is True
    assert decision.authorization_state == ActionState.OVERRIDDEN


def test_release_request_without_reviewer_fails_closed():
    with pytest.raises(ValueError, match="identified reviewer"):
        evaluate_release_gate((_finding("NOMINAL"),), release_requested=True)


def test_exception_cannot_be_used_when_health_is_nominal():
    with pytest.raises(ValueError, match="invalid when health is nominal"):
        evaluate_release_gate(
            (_finding("NOMINAL"),),
            reviewer="REVIEWER-1",
            release_requested=True,
            explicit_degraded_override=True,
        )

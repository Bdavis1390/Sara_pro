from __future__ import annotations

from worldshepherd_sara.ddil import Envelope
from worldshepherd_sara.ddil_campaign import run_ddil_campaign
from worldshepherd_sara.evidence_artifacts import ComparisonOperator, ExpectedResult
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
    canonical_digest,
)
from worldshepherd_sara.qualification_eval import evaluate_all_expected_results


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0099",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="Synthetic DDIL qualification requirement",
            agency="Worldshepherd internal test",
            url="internal://pre/ddil-v1",
            source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Exercise deterministic degraded-message handling before external validation.",
        recurrence="Reusable readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["DDIL", "mission assurance"],
        existing_capability=["synthetic transport-fault harness"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["real tactical-network validation"],
        claims_boundary=["No RF or operational DDIL claim"],
    )


def test_expected_result_evaluator_is_explicit_and_fail_closed_on_missing_metric():
    expected = [
        ExpectedResult(metric="latency_ms", operator=ComparisonOperator.LE, target=100),
        ExpectedResult(metric="passed", operator=ComparisonOperator.EQ, target=True),
    ]
    ok, outcomes = evaluate_all_expected_results(
        expected, {"latency_ms": 90, "passed": True}
    )
    assert ok is True
    assert outcomes == {"latency_ms": True, "passed": True}
    missing_ok, missing = evaluate_all_expected_results(expected, {"latency_ms": 90})
    assert missing_ok is False
    assert missing["passed"] is False


def test_ddil_campaign_is_replayable_and_claims_bounded():
    messages = [
        Envelope(sequence=i, source="sim-node", payload={"value": i}, timestamp_ms=i * 100)
        for i in range(1, 7)
    ]
    first = run_ddil_campaign(
        messages=messages,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    second = run_ddil_campaign(
        messages=messages,
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert first["campaign"] == "DDIL_SYNTHETIC_V1"
    assert len(first["evidence"]) == 5
    assert all(item["result"] == "PASS" for item in first["evidence"])
    assert first["bundle_digest"] == second["bundle_digest"]
    without_digest = dict(first)
    digest = without_digest.pop("bundle_digest")
    assert digest == canonical_digest(without_digest)
    assert "no RF" in first["scope_note"].lower()

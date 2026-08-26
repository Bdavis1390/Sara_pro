from __future__ import annotations

from worldshepherd_sara.edge_qualification import qualify_host_callable
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
)


def _requirement() -> RequirementDeltaRecord:
    return RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0018",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(title="Edge-AI benchmark readiness target", agency="Worldshepherd PRE", url="internal://pre/edge-benchmark-v1", source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, retrieved_utc="2026-08-26T00:00:00Z"),
        statement="Benchmark deterministic local software behavior before target-device performance claims.",
        recurrence="Reusable edge-AI readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["edge AI","autonomy","C2","sensor fusion"],
        existing_capability=["host-specific Python benchmark harness"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["target edge hardware", "power/thermal measurement", "real-time validation"],
        claims_boundary=["Host-specific benchmark only"],
    )


def test_edge_qualification_is_replayable_in_output_and_device_claims_bounded():
    def transform(value: dict) -> dict:
        return {"total": sum(value["values"]), "count": len(value["values"])}

    bundle = qualify_host_callable(
        function=transform,
        input_value={"values":[1,2,3,4]},
        requirement=_requirement(),
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
        environment={"runtime":"pytest-python"},
        repetitions=3,
        warmup=1,
    )
    record = bundle["evidence"][0]
    assert record["result"] == "PASS"
    assert record["outputs"][0]["deterministic_output"] is True
    assert len(set(record["outputs"][0]["output_digests"])) == 1
    assert "no GPU/NPU" in bundle["scope_note"]

from __future__ import annotations

from worldshepherd_sara.ddil_rejoin_qualification import qualify_partition_rejoin
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
        requirement_delta_id="PRE-RD-2026-0019",
        demand_class=DemandClass.EMERGING_DEMAND,
        source=SourceRecord(title="DDIL partition/rejoin readiness target", agency="Worldshepherd PRE", url="internal://pre/ddil-rejoin-v1", source_status=SourceStatus.PRIMARY_TECHNICAL_SOURCE, retrieved_utc="2026-08-26T00:00:00Z"),
        statement="Reconcile non-conflicting state after partition while surfacing equal-authority divergence for policy/human resolution.",
        recurrence="Reusable DDIL/C2/autonomy readiness requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["DDIL","C2","autonomy","configuration custody"],
        existing_capability=["deterministic conflict-visible reconciliation policy"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["distributed deployment", "real network partitions", "consensus validation"],
        claims_boundary=["Synthetic reconciliation only"],
    )


def test_partition_rejoin_qualification_surfaces_equal_authority_conflict():
    bundle = qualify_partition_rejoin(requirement=_requirement(), software_commit="test-commit", executed_utc="2026-08-26T00:00:00Z", operator="pytest")
    record = bundle["evidence"][0]
    assert record["result"] == "PASS"
    output = record["outputs"][0]
    assert output["task_state"] == "MERGED"
    assert output["task_selected_value"] == "resume"
    assert output["mode_state"] == "CONFLICT"
    assert output["mode_selected"] is None
    assert "no distributed-consensus" in bundle["scope_note"]

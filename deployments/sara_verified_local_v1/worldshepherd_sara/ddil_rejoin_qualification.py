from __future__ import annotations

from typing import Any

from .ddil_reconcile import ReconciliationState, VersionedState, reconcile_maps
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_partition_rejoin(
    *,
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    left = {
        "task": VersionedState(key="task", value="hold", logical_clock=4, authority=1, source_node="left"),
        "mode": VersionedState(key="mode", value="search", logical_clock=9, authority=1, source_node="left"),
    }
    right = {
        "task": VersionedState(key="task", value="resume", logical_clock=5, authority=1, source_node="right"),
        "mode": VersionedState(key="mode", value="return", logical_clock=9, authority=1, source_node="right"),
    }
    results = reconcile_maps(left, right)
    task = results["task"]
    mode = results["mode"]
    passed = (
        task.state == ReconciliationState.MERGED
        and task.selected is not None
        and task.selected.value == "resume"
        and mode.state == ReconciliationState.CONFLICT
        and mode.selected is None
    )

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-9201",
        requirement_id=requirement.requirement_delta_id,
        test_id="ddil_partition_rejoin_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest({"scenario":"synthetic-partition-rejoin-v1"}),
        configuration_digest=canonical_digest({"policy":"logical-clock-authority-visible-conflict-v1"}),
        inputs=[
            {"left": {key: value.__dict__ for key, value in left.items()}},
            {"right": {key: value.__dict__ for key, value in right.items()}},
        ],
        outputs=[
            {
                "task_state": task.state.value,
                "task_selected_value": task.selected.value if task.selected else None,
                "mode_state": mode.state.value,
                "mode_selected": None if mode.selected is None else mode.selected.value,
            }
        ],
        metrics=[
            {"name":"newer_state_selected", "value": task.selected is not None and task.selected.value == "resume"},
            {"name":"equal_authority_conflict_visible", "value": mode.state == ReconciliationState.CONFLICT},
            {"name":"conflict_not_silently_resolved", "value": mode.selected is None},
        ],
        uncertainty=[{"name":"distributed_consensus_validity", "state":"NOT_EVALUATED"}],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=("Synthetic partition/rejoin reconciliation selected newer non-conflicting state and surfaced equal-authority divergence" if passed else "Partition/rejoin reconciliation violated one or more frozen conflict-policy expectations"),
        negative_evidence=[] if passed else [{"task": task.state.value, "mode": mode.state.value}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["scope_note"] = "Synthetic partition/rejoin policy evidence only; no distributed-consensus, tactical-network, safety, or operational autonomy claim."
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle

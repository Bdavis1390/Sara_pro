from __future__ import annotations

from typing import Any

from .manufacturing_thread import ManufacturingDigitalThread
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_manufacturing_thread(
    *, fixture: dict[str, Any], requirement: RequirementDeltaRecord,
    software_commit: str, executed_utc: str, operator: str,
) -> dict[str, Any]:
    thread = ManufacturingDigitalThread.model_validate(fixture["thread"])
    expected = fixture["expected"]
    observed = {
        "qualification_state": thread.qualification_state(),
        "material_lot_count": len(thread.material_lots),
        "process_configuration_count": len(thread.process_configurations),
        "build_step_count": len(thread.build_steps),
        "specimen_count": len(thread.specimens),
        "thread_digest": thread.digest(),
    }
    passed = all(observed[key] == expected[key] for key in expected)

    evidence = QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-9002",
        requirement_id=requirement.requirement_delta_id,
        test_id="manufacturing_thread_synthetic_v1",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest=canonical_digest({"fixture_id": fixture["fixture_id"], "classification": fixture["classification"]}),
        configuration_digest=canonical_digest({"thread_schema": "ManufacturingDigitalThread"}),
        inputs=[{"thread_id": thread.thread_id}],
        outputs=[observed],
        metrics=[{"name": key, "value": observed[key], "expected": value} for key, value in expected.items()],
        uncertainty=[
            {"name": "physical_material_performance", "state": "NOT_EVALUATED"},
            {"name": "process_qualification", "state": "NOT_EVALUATED"},
        ],
        result=ResultStatus.PASS if passed else ResultStatus.FAIL,
        rationale=("Synthetic material-process-build-specimen lineage met frozen digital-thread expectations" if passed else "Synthetic manufacturing digital thread diverged from frozen expectations"),
        negative_evidence=[] if passed else [{"expected": expected, "observed": observed}],
        software_commit=software_commit,
        executed_utc=executed_utc,
        operator=operator,
        physical_validation_performed=False,
    )
    bundle = compile_qualification_bundle(requirement, [evidence])
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["thread_digest"] = thread.digest()
    bundle["scope_note"] = "Synthetic manufacturing digital-thread evidence only; no physical coupon, alloy-property, machine, DED process-qualification, or production-acceptance claim."
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle

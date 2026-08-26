from __future__ import annotations

from typing import Any

from .apnt import apnt_snapshot_graph, derive_apnt_decision
from .qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ResultStatus,
    canonical_digest,
    compile_qualification_bundle,
)


def qualify_synthetic_apnt_timeline(
    *,
    fixture: dict[str, Any],
    requirement: RequirementDeltaRecord,
    software_commit: str,
    executed_utc: str,
    operator: str,
) -> dict[str, Any]:
    """Evaluate the frozen synthetic APNT timeline and compile replayable evidence."""
    evidence: list[QualificationEvidenceRecord] = []
    last_graph = None

    env_digest = canonical_digest(
        {
            "fixture_id": fixture["fixture_id"],
            "classification": fixture["classification"],
        }
    )
    config_digest = canonical_digest({"model": "bounded_apnt_awareness_v1"})

    for index, point in enumerate(fixture["timeline"], start=1):
        decision = derive_apnt_decision(point["source_state"])
        expected = point["expected_operational_state"]
        passed = decision.operational_state == expected
        last_graph = apnt_snapshot_graph(
            graph_id=f"{fixture['fixture_id']}:t{point['t_seconds']}",
            source_state=point["source_state"],
            decision=decision,
        )
        evidence.append(
            QualificationEvidenceRecord(
                qualification_id=f"WS-QE-2026-{index:04d}",
                requirement_id=requirement.requirement_delta_id,
                test_id=f"apnt_state_t{point['t_seconds']}",
                evidence_scope=EvidenceScope.SOFTWARE,
                capability_status=CapabilityStatus.PROVEN_INTERNALLY,
                environment_digest=env_digest,
                configuration_digest=config_digest,
                inputs=[{"source_state": point["source_state"]}],
                outputs=[
                    {
                        "operational_state": decision.operational_state,
                        "recovery_options": list(decision.recovery_options),
                    }
                ],
                metrics=[
                    {
                        "name": "state_match",
                        "value": 1 if passed else 0,
                        "expected": expected,
                    }
                ],
                uncertainty=[
                    {"name": "physical_validity", "state": "NOT_EVALUATED"}
                ],
                result=ResultStatus.PASS if passed else ResultStatus.FAIL,
                rationale=(
                    "Synthetic bounded-awareness state matched frozen expectation"
                    if passed
                    else "Synthetic bounded-awareness state did not match frozen expectation"
                ),
                negative_evidence=(
                    []
                    if passed
                    else [
                        {
                            "expected": expected,
                            "observed": decision.operational_state,
                        }
                    ]
                ),
                software_commit=software_commit,
                executed_utc=executed_utc,
                operator=operator,
                physical_validation_performed=False,
            )
        )

    bundle = compile_qualification_bundle(requirement, evidence, last_graph)
    bundle.pop("bundle_digest", None)
    bundle["fixture_id"] = fixture["fixture_id"]
    bundle["scope_note"] = (
        "Synthetic software qualification only; no physical APNT or Navy operational claim."
    )
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle

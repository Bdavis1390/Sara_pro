from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .qualification import (
    QualificationEvidenceRecord,
    RequirementDeltaRecord,
    ReviewStatus,
    SupersessionState,
    canonical_digest,
)
from .tevv_athlon import TEVVAthlonPlan, TEVVMeasurement, plan_digest, validate_measurements


class QualificationTEVVBinding(BaseModel):
    """Explicitly bind one qualification metric to one TEVV Event/Block/Tool tuple.

    The bridge intentionally refuses implicit semantic matching. A human or a
    separately governed workflow must choose which qualification metric is
    evidence for which TEVV measurement concept.
    """

    binding_id: str = Field(pattern=r"^WS-TEVV-BIND-[0-9a-zA-Z._-]+$")
    qualification_id: str = Field(pattern=r"^WS-QE-[0-9]{4}-[0-9]{4,}$")
    metric_index: int = Field(ge=0)
    event_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    tool_id: str = Field(min_length=1)
    metric_name_override: str | None = None


def _metric_parts(metric: dict[str, Any], binding: QualificationTEVVBinding) -> tuple[str, Any, str | None, Any | None, bool | None]:
    name = binding.metric_name_override or metric.get("name") or metric.get("metric") or metric.get("id")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"qualification metric {binding.qualification_id}[{binding.metric_index}] requires a name/metric/id or metric_name_override"
        )
    if "value" not in metric:
        raise ValueError(
            f"qualification metric {binding.qualification_id}[{binding.metric_index}] requires an explicit value"
        )
    units = metric.get("units")
    if units is not None and not isinstance(units, str):
        raise ValueError("metric units must be a string when provided")
    passed = metric.get("passed_acceptance_rule")
    if passed is not None and not isinstance(passed, bool):
        raise ValueError("passed_acceptance_rule must be boolean when provided")
    return name.strip(), metric["value"], units, metric.get("uncertainty"), passed


def qualification_measurements(
    plan: TEVVAthlonPlan,
    evidence: list[QualificationEvidenceRecord],
    bindings: list[QualificationTEVVBinding],
) -> list[TEVVMeasurement]:
    """Create TEVV measurement candidates from explicitly bound qualification metrics.

    This function does not infer acceptance from a qualification record's PASS
    status, does not promote review state, and does not claim physical or
    external validation. Event/Block/Tool membership is revalidated against the
    supplied TEVV plan before returning measurements.
    """

    by_id: dict[str, QualificationEvidenceRecord] = {}
    for record in evidence:
        if record.qualification_id in by_id:
            raise ValueError(f"duplicate qualification evidence ID: {record.qualification_id}")
        by_id[record.qualification_id] = record

    seen_binding_ids: set[str] = set()
    seen_coordinates: set[tuple[str, int, str, str, str]] = set()
    measurements: list[TEVVMeasurement] = []

    for binding in bindings:
        if binding.binding_id in seen_binding_ids:
            raise ValueError(f"duplicate TEVV binding ID: {binding.binding_id}")
        seen_binding_ids.add(binding.binding_id)

        coordinate = (
            binding.qualification_id,
            binding.metric_index,
            binding.event_id,
            binding.block_id,
            binding.tool_id,
        )
        if coordinate in seen_coordinates:
            raise ValueError(f"duplicate qualification-to-TEVV coordinate: {coordinate}")
        seen_coordinates.add(coordinate)

        record = by_id.get(binding.qualification_id)
        if record is None:
            raise ValueError(f"binding references unknown qualification evidence: {binding.qualification_id}")
        if record.supersession.state is not SupersessionState.CURRENT:
            raise ValueError(
                f"qualification evidence {record.qualification_id} is not CURRENT: {record.supersession.state.value}"
            )
        if record.review.status is ReviewStatus.REJECTED:
            raise ValueError(f"qualification evidence {record.qualification_id} was rejected in review")
        if binding.metric_index >= len(record.metrics):
            raise ValueError(
                f"qualification metric index out of range for {record.qualification_id}: {binding.metric_index}"
            )

        metric = record.metrics[binding.metric_index]
        if not isinstance(metric, dict):
            raise ValueError("qualification metrics must be mappings")
        name, value, units, metric_uncertainty, passed = _metric_parts(metric, binding)
        uncertainty: Any | None = metric_uncertainty
        if uncertainty is None and record.uncertainty:
            uncertainty = record.uncertainty

        source_refs = [
            record.qualification_id,
            record.environment_digest,
            record.configuration_digest,
        ]
        if record.software_commit:
            source_refs.append(record.software_commit)

        measurements.append(
            TEVVMeasurement(
                measurement_id=f"{binding.binding_id}-M",
                event_id=binding.event_id,
                block_id=binding.block_id,
                tool_id=binding.tool_id,
                metric=name,
                value=value,
                units=units,
                source_refs=source_refs,
                uncertainty=uncertainty,
                passed_acceptance_rule=passed,
            )
        )

    validate_measurements(plan, measurements)
    return measurements


def compile_tevv_qualification_bundle(
    requirement: RequirementDeltaRecord,
    plan: TEVVAthlonPlan,
    evidence: list[QualificationEvidenceRecord],
    bindings: list[QualificationTEVVBinding],
) -> dict[str, Any]:
    """Compile a digest-bound PRE/PVK -> PRIME-TEVV handoff artifact.

    The bundle is an evidence handoff, not a TEVV decision or an authorization
    to execute. It retains negative evidence and review state, and it never
    upgrades software/simulation evidence into physical validation.
    """

    for record in evidence:
        if record.requirement_id != requirement.requirement_delta_id:
            raise ValueError(
                f"qualification evidence {record.qualification_id} requirement_id {record.requirement_id!r} "
                f"does not match {requirement.requirement_delta_id!r}"
            )

    measurements = qualification_measurements(plan, evidence, bindings)
    evidence_index = [
        {
            "qualification_id": record.qualification_id,
            "record_digest": canonical_digest(record),
            "result": record.result.value,
            "evidence_scope": record.evidence_scope.value,
            "capability_status": record.capability_status.value,
            "review_status": record.review.status.value,
            "supersession_state": record.supersession.state.value,
            "physical_validation_performed": record.physical_validation_performed,
        }
        for record in evidence
    ]
    negative_evidence = [
        {
            "qualification_id": record.qualification_id,
            "items": record.negative_evidence,
        }
        for record in evidence
        if record.negative_evidence
    ]
    unreviewed = [
        record.qualification_id
        for record in evidence
        if record.review.status is ReviewStatus.UNREVIEWED
    ]
    physical_scope_present = any(
        record.evidence_scope.value == "PHYSICAL" for record in evidence
    ) or any(event.physical_execution_required for event in plan.events)

    bundle: dict[str, Any] = {
        "schema": "ws-prime-tevv-qualification-bridge-1",
        "requirement_id": requirement.requirement_delta_id,
        "requirement_digest": canonical_digest(requirement),
        "plan_id": plan.plan_id,
        "plan_digest": plan_digest(plan),
        "capture_ready_source": requirement.capture_ready(),
        "measurement_candidates": [item.model_dump(mode="json") for item in measurements],
        "evidence_index": evidence_index,
        "negative_evidence": negative_evidence,
        "unreviewed_qualification_ids": unreviewed,
        "human_review_pending": bool(unreviewed),
        "physical_scope_present": physical_scope_present,
        "physical_validation_claimed": False,
        "external_execution_claimed": False,
        "nist_conformance_claimed": False,
        "claims_boundary": [
            "This artifact binds existing qualification evidence to a PRIME-TEVV plan; it is not itself a TEVV decision.",
            "Qualification PASS status is not automatically converted into a TEVV acceptance-rule pass.",
            "Software or simulation evidence cannot establish physical validation, field performance, certification, accreditation, partner validation, or operational authority.",
            "Use of the NIST AI 200-2 initial public draft structure does not establish NIST conformance, endorsement, certification, or approval.",
            *requirement.claims_boundary,
        ],
    }
    bundle["bundle_digest"] = canonical_digest(bundle)
    return bundle


def verify_tevv_qualification_bundle(bundle: dict[str, Any]) -> bool:
    payload = dict(bundle)
    claimed = payload.pop("bundle_digest", None)
    return isinstance(claimed, str) and claimed == canonical_digest(payload)

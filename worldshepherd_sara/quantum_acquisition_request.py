"""Generate evidence-complete acquisition/test requests from QRF campaign gates.

This module turns the machine-enforced campaign definition into partner/lab-facing
request packages. A request package is a template only; placeholders are never
accepted as evidence and cannot advance mission readiness.
"""

from __future__ import annotations

from dataclasses import dataclass

from worldshepherd_sara.quantum_external_campaign import CampaignGate, build_external_campaigns
from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceType


_BASE_FIELDS: dict[ExternalEvidenceType, tuple[str, ...]] = {
    ExternalEvidenceType.QPU_EXECUTION: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "backend_or_device",
        "job_or_run_id",
        "result_digest",
        "latency_seconds",
        "cost_usd",
    ),
    ExternalEvidenceType.QUANTUM_SENSOR: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "backend_or_device",
        "calibration_id",
        "truth_reference_id",
        "uncertainty",
    ),
    ExternalEvidenceType.MATERIALS_HAMILTONIAN: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "classical_baseline_digest",
        "metadata.structure_digest",
        "metadata.hamiltonian_digest",
        "metadata.basis",
        "metadata.active_space",
    ),
    ExternalEvidenceType.CALIBRATED_PHYSICS_MODEL: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "truth_reference_id",
        "uncertainty",
        "classical_baseline_digest",
    ),
    ExternalEvidenceType.MISSION_OPTIMIZATION: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "classical_baseline_digest",
        "latency_seconds",
        "cost_usd",
        "metadata.instance_family_digest",
        "metadata.objective_definition",
        "metadata.constraint_definition",
    ),
    ExternalEvidenceType.PHYSICAL_METROLOGY: (
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
        "calibration_id",
        "truth_reference_id",
        "uncertainty",
        "metadata.null_controls_completed",
    ),
}


@dataclass(frozen=True)
class AcquisitionRequest:
    request_id: str
    project_id: str
    gate_id: str
    from_stage: str
    to_stage: str
    objective: str
    evidence_minimums: tuple[tuple[str, int], ...]
    required_record_fields: tuple[str, ...]
    required_metadata_keys: tuple[str, ...]
    allowed_environments: tuple[str, ...]
    preconditions: tuple[str, ...]
    minimum_distinct_providers: int
    minimum_distinct_devices: int
    deliverables: tuple[str, ...]
    acceptance_statement: str
    claim_control: str


def _find_gate(project_id: str, gate_id: str) -> CampaignGate:
    for campaign in build_external_campaigns():
        if campaign.project_id != project_id:
            continue
        for gate in campaign.gates:
            if gate.gate_id == gate_id:
                return gate
        raise KeyError(f"unknown gate {gate_id!r} for project {project_id!r}")
    raise KeyError(f"unknown project {project_id!r}")


def build_acquisition_request(project_id: str, gate_id: str) -> AcquisitionRequest:
    gate = _find_gate(project_id, gate_id)
    required_fields: set[str] = {
        "project_id",
        "evidence_type",
        "metadata.campaign_gate_id",
    }
    for minimum in gate.evidence_minimums:
        required_fields.update(_BASE_FIELDS[minimum.evidence_type])
    required_fields.update(f"metadata.{key}" for key in gate.required_metadata_keys)

    deliverables: list[str] = []
    for minimum in gate.evidence_minimums:
        deliverables.append(
            f"At least {minimum.minimum_records} structurally complete {minimum.evidence_type.value} record(s) bound to {gate.gate_id}."
        )
    if gate.preconditions:
        deliverables.append("Document completion of gate preconditions: " + ", ".join(gate.preconditions) + ".")
    if gate.minimum_distinct_providers:
        deliverables.append(f"Evidence must cover at least {gate.minimum_distinct_providers} distinct provider/lab identity(ies).")
    if gate.minimum_distinct_devices:
        deliverables.append(f"Evidence must cover at least {gate.minimum_distinct_devices} distinct backend/device identity(ies).")
    if gate.allowed_environments:
        deliverables.append("At least one accepted record must be collected in: " + ", ".join(gate.allowed_environments) + ".")
    deliverables.extend((
        "Provide raw artifacts or immutable references sufficient to independently recompute every supplied SHA-256 digest.",
        "Provide configuration, software/firmware/instrument identity, calibration/truth-reference information where applicable, and the frozen test protocol identity.",
        "Identify failed, aborted, excluded, or anomalous runs; do not report only successful runs.",
    ))

    return AcquisitionRequest(
        request_id=f"REQ-{gate.gate_id}",
        project_id=project_id,
        gate_id=gate.gate_id,
        from_stage=gate.from_stage.value,
        to_stage=gate.to_stage.value,
        objective=f"Acquire evidence sufficient to evaluate transition {gate.from_stage.value} -> {gate.to_stage.value} without stage skipping.",
        evidence_minimums=tuple((row.evidence_type.value, row.minimum_records) for row in gate.evidence_minimums),
        required_record_fields=tuple(sorted(required_fields)),
        required_metadata_keys=gate.required_metadata_keys,
        allowed_environments=gate.allowed_environments,
        preconditions=gate.preconditions,
        minimum_distinct_providers=gate.minimum_distinct_providers,
        minimum_distinct_devices=gate.minimum_distinct_devices,
        deliverables=tuple(deliverables),
        acceptance_statement=gate.acceptance_statement,
        claim_control=(
            "This is a request/template, not evidence. Completion means only that the requested package can be submitted to "
            "Worldshepherd evidence intake and technical review; it does not automatically advance readiness or validate a claim."
        ),
    )


def build_all_acquisition_requests() -> tuple[AcquisitionRequest, ...]:
    requests: list[AcquisitionRequest] = []
    for campaign in build_external_campaigns():
        for gate in campaign.gates:
            requests.append(build_acquisition_request(campaign.project_id, gate.gate_id))
    return tuple(requests)


def render_request_markdown(request: AcquisitionRequest, *, organization: str = "External partner/lab") -> str:
    evidence_lines = "\n".join(
        f"- {count} x `{evidence_type}`" for evidence_type, count in request.evidence_minimums
    ) or "- No external record at this gate; listed preconditions must be completed."
    field_lines = "\n".join(f"- `{field}`" for field in request.required_record_fields)
    deliverable_lines = "\n".join(f"- {item}" for item in request.deliverables)
    environment = ", ".join(request.allowed_environments) if request.allowed_environments else "not restricted by campaign definition"
    preconditions = ", ".join(request.preconditions) if request.preconditions else "none"
    return (
        f"# Worldshepherd Evidence Acquisition Request — {request.gate_id}\n\n"
        f"**To:** {organization}\n\n"
        f"**Project:** {request.project_id}\n\n"
        f"**Stage transition under evaluation:** `{request.from_stage}` -> `{request.to_stage}`\n\n"
        f"## Objective\n\n{request.objective}\n\n"
        f"## Evidence minimums\n\n{evidence_lines}\n\n"
        f"## Required record fields\n\n{field_lines}\n\n"
        f"## Environment\n\n{environment}\n\n"
        f"## Preconditions\n\n{preconditions}\n\n"
        f"## Deliverables\n\n{deliverable_lines}\n\n"
        f"## Gate acceptance statement\n\n{request.acceptance_statement}\n\n"
        f"## Claims control\n\n{request.claim_control}\n"
    )

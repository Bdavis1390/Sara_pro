"""Fail-closed local ingest for external QRF evidence packages.

External evidence must arrive as typed records bound to the *current* campaign gate.
At least the raw artifact is read locally and re-hashed before a record is eligible
for structural intake. Optional bindings may verify any other digest-bearing record
field or metadata field against a local artifact.

A successful ingest decision does not update mission readiness automatically. It
means only that the supplied package is structurally consistent with the current
campaign gate and is ready for separate technical review / controlled registration.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from worldshepherd_sara.quantum_external_campaign import (
    build_external_campaigns,
    evaluate_campaign,
)
from worldshepherd_sara.quantum_external_evidence import (
    ExternalEvidenceRecord,
    ExternalEvidenceType,
    validate_external_evidence,
)
from worldshepherd_sara.quantum_alti_structure import sha256_bytes


@dataclass(frozen=True)
class ArtifactBinding:
    field_path: str
    artifact_path: str


@dataclass(frozen=True)
class ExternalEvidenceEnvelope:
    record: ExternalEvidenceRecord
    artifact_bindings: tuple[ArtifactBinding, ...]


@dataclass(frozen=True)
class ArtifactVerification:
    field_path: str
    artifact_path: str
    expected_digest: str | None
    actual_digest: str | None
    verified: bool
    reason: str | None


@dataclass(frozen=True)
class RecordIngestDecision:
    source_id: str
    project_id: str
    gate_id: str | None
    structurally_accepted: bool
    current_gate_match: bool
    raw_artifact_verified: bool
    accepted_for_campaign_evaluation: bool
    reasons: tuple[str, ...]
    artifact_verifications: tuple[ArtifactVerification, ...]


@dataclass(frozen=True)
class ExternalEvidenceBatchDecision:
    project_id: str | None
    current_gate_id: str | None
    records_received: int
    records_accepted_for_campaign_evaluation: int
    record_decisions: tuple[RecordIngestDecision, ...]
    achieved_stage: str | None
    next_gate_id: str | None
    campaign_gate_satisfied: bool
    ready_for_technical_review: bool
    claim_control: str


def _record_value(record: ExternalEvidenceRecord, field_path: str) -> str | None:
    if field_path.startswith("metadata."):
        key = field_path.split(".", 1)[1]
        value = record.metadata.get(key)
    else:
        if not hasattr(record, field_path):
            return None
        value = getattr(record, field_path)
    if value is None:
        return None
    return str(value)


def _resolve_path(base_dir: Path, supplied: str) -> Path:
    path = Path(supplied).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _verify_binding(
    record: ExternalEvidenceRecord,
    binding: ArtifactBinding,
    *,
    base_dir: Path,
) -> ArtifactVerification:
    expected = _record_value(record, binding.field_path)
    path = _resolve_path(base_dir, binding.artifact_path)
    if expected is None:
        return ArtifactVerification(
            field_path=binding.field_path,
            artifact_path=str(path),
            expected_digest=None,
            actual_digest=None,
            verified=False,
            reason="field path does not resolve to a declared digest value",
        )
    if not path.is_file() or path.stat().st_size == 0:
        return ArtifactVerification(
            field_path=binding.field_path,
            artifact_path=str(path),
            expected_digest=expected,
            actual_digest=None,
            verified=False,
            reason="artifact does not exist or is empty",
        )
    actual = sha256_bytes(path.read_bytes())
    verified = actual.lower() == expected.lower()
    return ArtifactVerification(
        field_path=binding.field_path,
        artifact_path=str(path),
        expected_digest=expected,
        actual_digest=actual,
        verified=verified,
        reason=None if verified else "artifact digest does not match declared field",
    )


def external_record_from_mapping(payload: Mapping[str, Any]) -> ExternalEvidenceRecord:
    required = (
        "project_id",
        "evidence_type",
        "source_id",
        "raw_artifact_digest",
        "collected_utc",
        "provider_or_lab",
        "configuration_digest",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError("missing required record field(s): " + ", ".join(missing))
    try:
        evidence_type = ExternalEvidenceType(str(payload["evidence_type"]))
    except ValueError as exc:
        allowed = ", ".join(row.value for row in ExternalEvidenceType)
        raise ValueError(f"unsupported evidence_type; expected one of: {allowed}") from exc

    metadata_raw = payload.get("metadata", {})
    if not isinstance(metadata_raw, Mapping):
        raise ValueError("metadata must be an object/mapping")
    metadata = {str(key): str(value) for key, value in metadata_raw.items()}

    def optional_float(name: str) -> float | None:
        value = payload.get(name)
        if value is None:
            return None
        return float(value)

    return ExternalEvidenceRecord(
        project_id=str(payload["project_id"]),
        evidence_type=evidence_type,
        source_id=str(payload["source_id"]),
        raw_artifact_digest=str(payload["raw_artifact_digest"]),
        collected_utc=str(payload["collected_utc"]),
        provider_or_lab=str(payload["provider_or_lab"]),
        configuration_digest=str(payload["configuration_digest"]),
        repeat_count=int(payload.get("repeat_count", 1)),
        calibration_id=None if payload.get("calibration_id") is None else str(payload["calibration_id"]),
        truth_reference_id=None if payload.get("truth_reference_id") is None else str(payload["truth_reference_id"]),
        uncertainty=optional_float("uncertainty"),
        result_digest=None if payload.get("result_digest") is None else str(payload["result_digest"]),
        classical_baseline_digest=None if payload.get("classical_baseline_digest") is None else str(payload["classical_baseline_digest"]),
        job_or_run_id=None if payload.get("job_or_run_id") is None else str(payload["job_or_run_id"]),
        backend_or_device=None if payload.get("backend_or_device") is None else str(payload["backend_or_device"]),
        latency_seconds=optional_float("latency_seconds"),
        cost_usd=optional_float("cost_usd"),
        environment=None if payload.get("environment") is None else str(payload["environment"]),
        metadata=metadata,
    )


def envelope_from_mapping(payload: Mapping[str, Any]) -> ExternalEvidenceEnvelope:
    record_raw = payload.get("record")
    if not isinstance(record_raw, Mapping):
        raise ValueError("evidence envelope requires a record object")
    bindings_raw = payload.get("artifact_bindings", [])
    if not isinstance(bindings_raw, list):
        raise ValueError("artifact_bindings must be a list")
    bindings: list[ArtifactBinding] = []
    for index, item in enumerate(bindings_raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"artifact_bindings[{index}] must be an object")
        field_path = str(item.get("field_path", "")).strip()
        artifact_path = str(item.get("artifact_path", "")).strip()
        if not field_path or not artifact_path:
            raise ValueError(f"artifact_bindings[{index}] requires field_path and artifact_path")
        bindings.append(ArtifactBinding(field_path=field_path, artifact_path=artifact_path))
    return ExternalEvidenceEnvelope(record=external_record_from_mapping(record_raw), artifact_bindings=tuple(bindings))


def evaluate_external_evidence_batch(
    envelopes: Iterable[ExternalEvidenceEnvelope],
    *,
    base_dir: str | Path = ".",
    completed_preconditions: Iterable[str] = (),
) -> ExternalEvidenceBatchDecision:
    batch = tuple(envelopes)
    if not batch:
        return ExternalEvidenceBatchDecision(
            project_id=None,
            current_gate_id=None,
            records_received=0,
            records_accepted_for_campaign_evaluation=0,
            record_decisions=(),
            achieved_stage=None,
            next_gate_id=None,
            campaign_gate_satisfied=False,
            ready_for_technical_review=False,
            claim_control="Empty evidence batch cannot advance a campaign.",
        )

    project_ids = {envelope.record.project_id for envelope in batch}
    if len(project_ids) != 1:
        decisions = tuple(
            RecordIngestDecision(
                source_id=envelope.record.source_id,
                project_id=envelope.record.project_id,
                gate_id=envelope.record.metadata.get("campaign_gate_id"),
                structurally_accepted=False,
                current_gate_match=False,
                raw_artifact_verified=False,
                accepted_for_campaign_evaluation=False,
                reasons=("one ingest batch must contain exactly one project_id",),
                artifact_verifications=(),
            )
            for envelope in batch
        )
        return ExternalEvidenceBatchDecision(
            project_id=None,
            current_gate_id=None,
            records_received=len(batch),
            records_accepted_for_campaign_evaluation=0,
            record_decisions=decisions,
            achieved_stage=None,
            next_gate_id=None,
            campaign_gate_satisfied=False,
            ready_for_technical_review=False,
            claim_control="Mixed-project batch rejected; campaign evaluation is project-scoped.",
        )

    project_id = next(iter(project_ids))
    campaigns = {campaign.project_id: campaign for campaign in build_external_campaigns()}
    campaign = campaigns.get(project_id)
    if campaign is None:
        raise ValueError(f"project_id {project_id!r} is not an active QRF campaign")
    current_gate_id = campaign.gates[0].gate_id if campaign.gates else None
    base = Path(base_dir).resolve()

    accepted_records: list[ExternalEvidenceRecord] = []
    record_decisions: list[RecordIngestDecision] = []
    for envelope in batch:
        record = envelope.record
        reasons: list[str] = []
        intake = validate_external_evidence(record)
        if not intake.accepted_for_intake:
            reasons.extend(intake.reasons)

        gate_id = record.metadata.get("campaign_gate_id")
        current_match = current_gate_id is not None and gate_id == current_gate_id
        if not current_match:
            reasons.append(
                f"record campaign gate {gate_id!r} does not match current active gate {current_gate_id!r}"
            )

        binding_fields = [binding.field_path for binding in envelope.artifact_bindings]
        if "raw_artifact_digest" not in binding_fields:
            reasons.append("raw_artifact_digest must have a local artifact binding and be re-hashed at intake")
        if len(binding_fields) != len(set(binding_fields)):
            reasons.append("artifact binding field paths must be unique within a record")

        verifications = tuple(
            _verify_binding(record, binding, base_dir=base)
            for binding in envelope.artifact_bindings
        )
        raw_verified = any(
            row.field_path == "raw_artifact_digest" and row.verified
            for row in verifications
        )
        failed_bindings = [row for row in verifications if not row.verified]
        reasons.extend(
            f"artifact binding {row.field_path}: {row.reason}"
            for row in failed_bindings
        )

        accepted = intake.accepted_for_intake and current_match and raw_verified and not failed_bindings
        if accepted:
            accepted_records.append(record)
        record_decisions.append(
            RecordIngestDecision(
                source_id=record.source_id,
                project_id=record.project_id,
                gate_id=gate_id,
                structurally_accepted=intake.accepted_for_intake,
                current_gate_match=current_match,
                raw_artifact_verified=raw_verified,
                accepted_for_campaign_evaluation=accepted,
                reasons=tuple(reasons),
                artifact_verifications=verifications,
            )
        )

    evaluation = evaluate_campaign(
        campaign,
        accepted_records,
        completed_preconditions=completed_preconditions,
    )
    first_evaluation = evaluation.gate_evaluations[0] if evaluation.gate_evaluations else None
    gate_satisfied = bool(first_evaluation and first_evaluation.satisfied)
    ready = gate_satisfied and all(row.accepted_for_campaign_evaluation for row in record_decisions)

    return ExternalEvidenceBatchDecision(
        project_id=project_id,
        current_gate_id=current_gate_id,
        records_received=len(batch),
        records_accepted_for_campaign_evaluation=len(accepted_records),
        record_decisions=tuple(record_decisions),
        achieved_stage=evaluation.achieved_stage,
        next_gate_id=evaluation.next_gate_id,
        campaign_gate_satisfied=gate_satisfied,
        ready_for_technical_review=ready,
        claim_control=(
            "ready_for_technical_review means the current campaign gate is structurally satisfied by locally re-hashed evidence. "
            "No readiness score is changed automatically; scientific/engineering review, claims control, SARA registration and any "
            "stage promotion remain separate governed actions."
        ),
    )


def batch_decision_as_dict(decision: ExternalEvidenceBatchDecision) -> dict[str, Any]:
    return asdict(decision)

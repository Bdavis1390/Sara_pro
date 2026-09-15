"""Amazon Braket Hybrid Job evidence contract for provider-neutral QRF execution.

This module validates retained/exported Hybrid Job metadata and converts a completed
real-QPU job into QRF external evidence. It intentionally does not submit AWS work or
claim AWS access. A real job must still be created under the user's AWS account and its
source/result artifacts must be retained and hashed locally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType


_SHA = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_JOB_ARN = re.compile(r"^arn:aws[a-z-]*:braket:[a-z0-9-]+:[0-9]{12}:job/.+")
_DEVICE_ARN = re.compile(r"^arn:aws[a-z-]*:braket:[a-z0-9-]*:[0-9]*:device/.+")


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


@dataclass(frozen=True)
class BraketHybridJobRecord:
    job_arn: str
    job_name: str
    status: str
    device_arn: str
    provider: str
    created_at: str
    started_at: str
    ended_at: str
    container_image_uri: str
    container_image_digest: str
    source_artifact_digest: str
    result_artifact_digest: str
    program_digest: str
    output_s3_uri: str
    initial_queue_position: str | None
    cost_usd: float
    task_count: int
    shots_total: int
    result_distribution: Mapping[str, float]
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class BraketHybridJobDecision:
    accepted: bool
    reasons: tuple[str, ...]
    queue_seconds: float | None
    runtime_seconds: float | None
    end_to_end_seconds: float | None
    job_metadata_digest: str
    claim_control: str = (
        "Acceptance means a completed Braket Hybrid Job record has sufficient retained identity/provenance for QRF intake. "
        "It does not prove provider-independent reproduction, quantum advantage, or mission readiness."
    )


def validate_braket_hybrid_job(record: BraketHybridJobRecord) -> BraketHybridJobDecision:
    reasons: list[str] = []
    if not _JOB_ARN.fullmatch(record.job_arn):
        reasons.append("job_arn must be a valid Amazon Braket Hybrid Job ARN")
    if not _DEVICE_ARN.fullmatch(record.device_arn):
        reasons.append("device_arn must be a valid Amazon Braket device ARN")
    if "/qpu/" not in record.device_arn:
        reasons.append("provider-parity hardware evidence requires a Braket QPU device ARN, not a simulator/local target")
    if record.status != "COMPLETED":
        reasons.append("Braket Hybrid Job must have COMPLETED status")
    if not record.job_name.strip() or not record.provider.strip():
        reasons.append("job_name and provider are required")
    if not record.container_image_uri.strip():
        reasons.append("container_image_uri is required")
    if not record.output_s3_uri.startswith("s3://"):
        reasons.append("output_s3_uri must identify retained Amazon S3 output")
    for name in ("container_image_digest", "source_artifact_digest", "result_artifact_digest", "program_digest"):
        if not _SHA.fullmatch(str(getattr(record, name))):
            reasons.append(f"{name} must be a full sha256 digest")
    if record.cost_usd < 0:
        reasons.append("cost_usd must be non-negative")
    if record.task_count <= 0 or record.shots_total <= 0:
        reasons.append("task_count and shots_total must be positive")
    if not record.result_distribution:
        reasons.append("result_distribution is required for sampled cross-provider comparison")
    else:
        try:
            values = [float(value) for value in record.result_distribution.values()]
        except (TypeError, ValueError):
            reasons.append("result_distribution values must be numeric")
        else:
            if any(value < 0 for value in values) or sum(values) <= 0:
                reasons.append("result_distribution must be non-negative with positive total mass")

    created = _parse_time(record.created_at)
    started = _parse_time(record.started_at)
    ended = _parse_time(record.ended_at)
    if created is None or started is None or ended is None:
        reasons.append("created_at, started_at and ended_at must be timezone-aware ISO timestamps")
        queue_seconds = runtime_seconds = end_to_end_seconds = None
    elif not (created <= started <= ended):
        reasons.append("Braket timestamps must satisfy created_at <= started_at <= ended_at")
        queue_seconds = runtime_seconds = end_to_end_seconds = None
    else:
        queue_seconds = (started - created).total_seconds()
        runtime_seconds = (ended - started).total_seconds()
        end_to_end_seconds = (ended - created).total_seconds()

    return BraketHybridJobDecision(
        accepted=not reasons,
        reasons=tuple(reasons),
        queue_seconds=queue_seconds,
        runtime_seconds=runtime_seconds,
        end_to_end_seconds=end_to_end_seconds,
        job_metadata_digest=_digest_json(asdict(record)),
    )


def build_braket_qpu_external_evidence(
    record: BraketHybridJobRecord,
    *,
    project_id: str,
    campaign_gate_id: str,
) -> ExternalEvidenceRecord:
    decision = validate_braket_hybrid_job(record)
    if not decision.accepted:
        raise ValueError(f"Braket Hybrid Job record is not evidence-complete: {decision.reasons}")
    assert decision.end_to_end_seconds is not None
    configuration = {
        "job_arn": record.job_arn,
        "device_arn": record.device_arn,
        "provider": record.provider,
        "container_image_digest": record.container_image_digest,
        "source_artifact_digest": record.source_artifact_digest,
        "program_digest": record.program_digest,
        "task_count": record.task_count,
        "shots_total": record.shots_total,
    }
    return ExternalEvidenceRecord(
        project_id=project_id,
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id=record.job_arn,
        raw_artifact_digest=record.result_artifact_digest,
        collected_utc=record.ended_at.replace("+00:00", "Z"),
        provider_or_lab=f"Amazon Braket / {record.provider}",
        configuration_digest=_digest_json(configuration),
        repeat_count=1,
        result_digest=record.result_artifact_digest,
        job_or_run_id=record.job_arn,
        backend_or_device=record.device_arn,
        latency_seconds=decision.end_to_end_seconds,
        cost_usd=record.cost_usd,
        environment="amazon_braket_hybrid_job_qpu",
        metadata={
            "campaign_gate_id": campaign_gate_id,
            "program_digest": record.program_digest,
            "container_image_uri": record.container_image_uri,
            "container_image_digest": record.container_image_digest,
            "source_artifact_digest": record.source_artifact_digest,
            "job_metadata_digest": decision.job_metadata_digest,
            "output_s3_uri": record.output_s3_uri,
            "queue_seconds": str(decision.queue_seconds),
            "runtime_seconds": str(decision.runtime_seconds),
            "initial_queue_position": record.initial_queue_position or "not_recorded",
            "task_count": str(record.task_count),
            "shots_total": str(record.shots_total),
            "provider": record.provider,
        },
    )

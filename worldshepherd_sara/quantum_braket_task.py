"""Governed Amazon Braket on-demand QPU task execution for QRF-BELL-001.

The existing :mod:`quantum_braket` contract covers Amazon Braket Hybrid Jobs. This
module covers the lighter-weight on-demand quantum-task path that is appropriate for
a shallow Bell benchmark. It deliberately keeps provider execution separate from
canonical workload identity and from mission-readiness promotion.

No AWS credentials are accepted by these APIs. The real submitter relies on the
normal AWS SDK credential chain / AWS_PROFILE configured outside Worldshepherd.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType


_SHA = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_TASK_ARN = re.compile(r"^arn:aws[a-z-]*:braket:[a-z0-9-]+:[0-9]{12}:quantum-task/.+")
_DEVICE_ARN = re.compile(r"^arn:aws[a-z-]*:braket:[a-z0-9-]*:[0-9]*:device/.+")
_QPU_DEVICE_MARKER = ":device/qpu/"

BRAKET_BELL_SUBMISSION_SPEC: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("cnot", (0, 1)),
)


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def sha256_text(text: str) -> str:
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


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


def _iso_utc(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    text = str(value)
    parsed = _parse_time(text)
    if parsed is None:
        return text
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso_utc(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "dict"):
        try:
            return _jsonable(value.dict())
        except TypeError:
            pass
    if hasattr(value, "json"):
        try:
            return json.loads(value.json())
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _provider_from_device_arn(device_arn: str) -> str:
    if _QPU_DEVICE_MARKER not in device_arn:
        return "unknown"
    remainder = device_arn.split(_QPU_DEVICE_MARKER, 1)[1]
    return remainder.split("/", 1)[0]


@dataclass(frozen=True)
class BraketQuantumTaskRecord:
    quantum_task_arn: str
    status: str
    device_arn: str
    provider: str
    created_at: str
    ended_at: str
    output_s3_uri: str
    shots_requested: int
    shots_successful: int
    canonical_program_digest: str
    submission_spec_digest: str
    device_snapshot_digest: str
    result_artifact_digest: str
    result_distribution: Mapping[str, float]
    cost_usd: float
    cost_basis: str
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class BraketQuantumTaskDecision:
    accepted: bool
    reasons: tuple[str, ...]
    end_to_end_seconds: float | None
    task_metadata_digest: str
    claim_control: str = (
        "Acceptance means a completed Amazon Braket on-demand QPU task record is structurally complete for QRF intake. "
        "It does not prove cross-provider reproduction, quantum advantage, billing accuracy, or mission readiness."
    )


def validate_braket_quantum_task(record: BraketQuantumTaskRecord) -> BraketQuantumTaskDecision:
    reasons: list[str] = []
    if not _TASK_ARN.fullmatch(record.quantum_task_arn):
        reasons.append("quantum_task_arn must be a valid Amazon Braket quantum-task ARN")
    if not _DEVICE_ARN.fullmatch(record.device_arn):
        reasons.append("device_arn must be a valid Amazon Braket device ARN")
    if _QPU_DEVICE_MARKER not in record.device_arn:
        reasons.append("hardware evidence requires a Braket QPU device ARN")
    if record.status != "COMPLETED":
        reasons.append("Amazon Braket quantum task must have COMPLETED status")
    if not record.provider.strip() or record.provider == "unknown":
        reasons.append("provider must be resolved from the executed QPU device")
    if not record.output_s3_uri.startswith("s3://"):
        reasons.append("output_s3_uri must identify retained Amazon S3 task output")
    for name in (
        "canonical_program_digest",
        "submission_spec_digest",
        "device_snapshot_digest",
        "result_artifact_digest",
    ):
        if not _SHA.fullmatch(str(getattr(record, name))):
            reasons.append(f"{name} must be a full sha256 digest")
    if record.shots_requested <= 0:
        reasons.append("shots_requested must be positive")
    if record.shots_successful <= 0 or record.shots_successful > record.shots_requested:
        reasons.append("shots_successful must be in [1, shots_requested]")
    if record.cost_usd < 0:
        reasons.append("cost_usd must be non-negative")
    if not record.cost_basis.strip():
        reasons.append("cost_basis must identify how execution cost was recorded")
    if not record.result_distribution:
        reasons.append("result_distribution is required")
    else:
        try:
            values = [float(value) for value in record.result_distribution.values()]
        except (TypeError, ValueError):
            reasons.append("result_distribution values must be numeric")
        else:
            total = sum(values)
            if any(value < 0 for value in values) or total <= 0:
                reasons.append("result_distribution must be non-negative with positive total mass")

    created = _parse_time(record.created_at)
    ended = _parse_time(record.ended_at)
    if created is None or ended is None:
        reasons.append("created_at and ended_at must be timezone-aware ISO timestamps")
        latency = None
    elif ended < created:
        reasons.append("Braket timestamps must satisfy created_at <= ended_at")
        latency = None
    else:
        latency = (ended - created).total_seconds()

    return BraketQuantumTaskDecision(
        accepted=not reasons,
        reasons=tuple(reasons),
        end_to_end_seconds=latency,
        task_metadata_digest=_digest_json(asdict(record)),
    )


def build_braket_task_external_evidence(
    record: BraketQuantumTaskRecord,
    *,
    project_id: str,
    campaign_gate_id: str,
) -> ExternalEvidenceRecord:
    decision = validate_braket_quantum_task(record)
    if not decision.accepted:
        raise ValueError(f"Braket quantum-task record is not evidence-complete: {decision.reasons}")
    assert decision.end_to_end_seconds is not None
    configuration = {
        "device_arn": record.device_arn,
        "provider": record.provider,
        "canonical_program_digest": record.canonical_program_digest,
        "submission_spec_digest": record.submission_spec_digest,
        "device_snapshot_digest": record.device_snapshot_digest,
        "shots_requested": record.shots_requested,
    }
    return ExternalEvidenceRecord(
        project_id=project_id,
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id=record.quantum_task_arn,
        raw_artifact_digest=record.result_artifact_digest,
        collected_utc=record.ended_at.replace("+00:00", "Z"),
        provider_or_lab=f"Amazon Braket / {record.provider}",
        configuration_digest=_digest_json(configuration),
        repeat_count=1,
        result_digest=record.result_artifact_digest,
        job_or_run_id=record.quantum_task_arn,
        backend_or_device=record.device_arn,
        latency_seconds=decision.end_to_end_seconds,
        cost_usd=record.cost_usd,
        environment="amazon_braket_on_demand_qpu",
        metadata={
            "campaign_gate_id": campaign_gate_id,
            "canonical_program_digest": record.canonical_program_digest,
            "submission_spec_digest": record.submission_spec_digest,
            "device_snapshot_digest": record.device_snapshot_digest,
            "task_metadata_digest": decision.task_metadata_digest,
            "output_s3_uri": record.output_s3_uri,
            "shots_requested": str(record.shots_requested),
            "shots_successful": str(record.shots_successful),
            "provider": record.provider,
            "cost_basis": record.cost_basis,
            **{str(key): str(value) for key, value in record.metadata.items()},
        },
    )


def _real_braket_submitter(
    *,
    device_arn: str,
    shots: int,
    s3_location: tuple[str, str],
    poll_timeout_seconds: int,
) -> dict[str, Any]:
    """Submit the frozen logical Bell workload using the official Braket SDK.

    AWS authentication is resolved only through the normal AWS SDK credential chain.
    This function never accepts access-key or secret-key values.
    """

    from braket.aws import AwsDevice  # type: ignore[import-not-found]
    from braket.circuits import Circuit  # type: ignore[import-not-found]

    device = AwsDevice(device_arn)
    circuit = Circuit().h(0).cnot(0, 1)
    task = device.run(
        circuit,
        s3_location,
        shots=shots,
        poll_timeout_seconds=poll_timeout_seconds,
    )
    task_result = task.result()
    metadata = _jsonable(task.metadata())
    return {
        "task_id": str(task.id),
        "task_metadata": metadata,
        "measurement_counts": {str(key): int(value) for key, value in task_result.measurement_counts.items()},
        "measurement_probabilities": {
            str(key): float(value) for key, value in task_result.measurement_probabilities.items()
        },
        "device_name": str(getattr(device, "name", "not_recorded")),
        "device_status_at_submission": str(getattr(device, "status", "not_recorded")),
        "device_snapshot": _jsonable(getattr(device, "properties", "not_recorded")),
    }


def execute_braket_bell_task(
    *,
    canonical_program_source: str,
    device_arn: str,
    shots: int,
    s3_bucket: str,
    s3_prefix: str,
    per_task_usd: float,
    per_shot_usd: float,
    pricing_source: str,
    poll_timeout_seconds: int = 86400,
    submitter: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute/normalize one Braket Bell task and return an unhashed raw artifact payload.

    ``submitter`` is dependency-injected by tests. Production calls use the official
    Amazon Braket SDK. The returned payload must be written locally and SHA-256 hashed
    before constructing :class:`BraketQuantumTaskRecord`.
    """

    if _QPU_DEVICE_MARKER not in device_arn or not _DEVICE_ARN.fullmatch(device_arn):
        raise ValueError("device_arn must identify an Amazon Braket QPU")
    if shots <= 0:
        raise ValueError("shots must be positive")
    if not s3_bucket.strip() or not s3_prefix.strip():
        raise ValueError("s3_bucket and s3_prefix are required")
    if per_task_usd < 0 or per_shot_usd < 0:
        raise ValueError("pricing rates must be non-negative")
    if not pricing_source.strip():
        raise ValueError("pricing_source is required")
    if poll_timeout_seconds <= 0:
        raise ValueError("poll_timeout_seconds must be positive")

    submit = submitter or _real_braket_submitter
    submitted = dict(
        submit(
            device_arn=device_arn,
            shots=shots,
            s3_location=(s3_bucket, s3_prefix),
            poll_timeout_seconds=poll_timeout_seconds,
        )
    )
    task_metadata = _jsonable(submitted.get("task_metadata", {}))
    if not isinstance(task_metadata, Mapping):
        raise ValueError("Braket task metadata must be a mapping")

    actual_task_arn = str(task_metadata.get("quantumTaskArn") or submitted.get("task_id") or "")
    actual_device_arn = str(task_metadata.get("deviceArn") or "")
    if actual_device_arn != device_arn:
        raise ValueError("Braket executed device ARN does not match the frozen requested device ARN")
    if str(task_metadata.get("status")) != "COMPLETED":
        raise ValueError("Braket task did not complete successfully")

    requested = int(task_metadata.get("shots", shots))
    successful = int(task_metadata.get("numSuccessfulShots", requested))
    counts = {str(key): int(value) for key, value in dict(submitted.get("measurement_counts", {})).items()}
    probabilities = {
        str(key): float(value) for key, value in dict(submitted.get("measurement_probabilities", {})).items()
    }
    distribution: Mapping[str, float] = probabilities if probabilities else counts
    if not distribution:
        raise ValueError("completed Braket task returned no sampled measurement distribution")

    bucket = str(task_metadata.get("outputS3Bucket") or s3_bucket)
    directory = str(task_metadata.get("outputS3Directory") or s3_prefix)
    output_s3_uri = f"s3://{bucket}/{directory.lstrip('/')}"
    program_digest = sha256_text(canonical_program_source)
    submission_spec = [[gate, list(qubits)] for gate, qubits in BRAKET_BELL_SUBMISSION_SPEC]
    device_snapshot = _jsonable(submitted.get("device_snapshot", "not_recorded"))
    cost_usd = per_task_usd + per_shot_usd * requested

    return {
        "schema_version": "1.0",
        "evidence_class": "amazon_braket_on_demand_qpu_raw_task",
        "quantum_task_arn": actual_task_arn,
        "device_arn": actual_device_arn,
        "provider": _provider_from_device_arn(actual_device_arn),
        "device_name": str(submitted.get("device_name", "not_recorded")),
        "device_status_at_submission": str(submitted.get("device_status_at_submission", "not_recorded")),
        "task_metadata": task_metadata,
        "output_s3_uri": output_s3_uri,
        "shots_requested": requested,
        "shots_successful": successful,
        "measurement_counts": counts,
        "measurement_probabilities": probabilities,
        "result_distribution": dict(distribution),
        "canonical_program_source": canonical_program_source,
        "canonical_program_digest": program_digest,
        "braket_submission_spec": submission_spec,
        "submission_spec_digest": _digest_json(submission_spec),
        "device_snapshot": device_snapshot,
        "device_snapshot_digest": _digest_json(device_snapshot),
        "cost_usd_predeclared_estimate": cost_usd,
        "cost_basis": (
            f"predeclared Braket rate estimate: task={per_task_usd:.12g} USD + "
            f"shots({requested})*{per_shot_usd:.12g} USD; reconcile against AWS billing if available"
        ),
        "pricing_source": pricing_source,
        "claim_control": (
            "This raw payload records one Amazon Braket on-demand QPU task. The cost is a predeclared rate estimate, not an AWS invoice. "
            "The task cannot promote readiness until the local artifact is hashed, structurally ingested, technically reviewed by an "
            "identified human, and separately approved for canonical state change."
        ),
    }


def record_from_raw_payload(raw_payload: Mapping[str, Any], *, result_artifact_digest: str) -> BraketQuantumTaskRecord:
    if not _SHA.fullmatch(result_artifact_digest):
        raise ValueError("result_artifact_digest must be a full sha256 digest")
    metadata = dict(raw_payload.get("task_metadata", {}))
    created = _iso_utc(metadata.get("createdAt", ""))
    ended = _iso_utc(metadata.get("endedAt", ""))
    return BraketQuantumTaskRecord(
        quantum_task_arn=str(raw_payload.get("quantum_task_arn", "")),
        status=str(metadata.get("status", "")),
        device_arn=str(raw_payload.get("device_arn", "")),
        provider=str(raw_payload.get("provider", "")),
        created_at=created,
        ended_at=ended,
        output_s3_uri=str(raw_payload.get("output_s3_uri", "")),
        shots_requested=int(raw_payload.get("shots_requested", 0)),
        shots_successful=int(raw_payload.get("shots_successful", 0)),
        canonical_program_digest=str(raw_payload.get("canonical_program_digest", "")),
        submission_spec_digest=str(raw_payload.get("submission_spec_digest", "")),
        device_snapshot_digest=str(raw_payload.get("device_snapshot_digest", "")),
        result_artifact_digest=result_artifact_digest,
        result_distribution={
            str(key): float(value) for key, value in dict(raw_payload.get("result_distribution", {})).items()
        },
        cost_usd=float(raw_payload.get("cost_usd_predeclared_estimate", -1)),
        cost_basis=str(raw_payload.get("cost_basis", "")),
        metadata={
            "pricing_source": str(raw_payload.get("pricing_source", "")),
            "cost_is_estimate_not_invoice": "true",
            "device_name": str(raw_payload.get("device_name", "not_recorded")),
            "device_status_at_submission": str(raw_payload.get("device_status_at_submission", "not_recorded")),
        },
    )

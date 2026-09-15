"""Provider-neutral gate-model execution normalization for QRF.

Vendor adapters emit rich raw records, then normalize into this schema for
cross-provider reproduction. Normalization never upgrades simulation or incomplete
provider records to QPU evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from worldshepherd_sara.quantum_readiness import BackendClass, EvidenceLevel, QuantumBackendRecord, QuantumDomain, QuantumRunEvidence


@dataclass(frozen=True)
class GateModelExecutionRecord:
    provider: str
    backend: str
    modality: str
    job_id: str
    collected_utc: str
    shots: int
    canonical_program_digest: str
    compiled_program_digest: str
    result_digest: str
    configuration_digest: str
    raw_artifact_digest: str
    outcome_distribution: Mapping[str, float]
    queue_seconds: float
    latency_seconds: float
    cost_usd: float
    calibration_id: str | None = None
    backend_properties_digest: str | None = None
    native_gate_set: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)


def _sha256(value: str) -> bool:
    if not value.startswith("sha256:"):
        return False
    body = value.split(":", 1)[1]
    return len(body) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in body)


def validate_gate_model_execution(record: GateModelExecutionRecord) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if not record.provider.strip() or not record.backend.strip() or not record.job_id.strip():
        reasons.append("provider, backend, and job_id are required")
    if "simulator" in record.backend.lower() or record.metadata.get("simulator", "false").lower() == "true":
        reasons.append("provider-neutral hardware evidence cannot use a simulator")
    if record.shots <= 0:
        reasons.append("shots must be positive")
    for name in ("canonical_program_digest", "compiled_program_digest", "result_digest", "configuration_digest", "raw_artifact_digest"):
        if not _sha256(str(getattr(record, name))):
            reasons.append(f"{name} must be a full sha256 identity")
    if record.backend_properties_digest is not None and not _sha256(record.backend_properties_digest):
        reasons.append("backend_properties_digest must be sha256 when supplied")
    if record.queue_seconds < 0 or record.latency_seconds < 0 or record.cost_usd < 0:
        reasons.append("queue, latency, and cost must be non-negative")
    if "T" not in record.collected_utc or not record.collected_utc.endswith("Z"):
        reasons.append("collected_utc must be an explicit UTC timestamp ending in Z")
    if not record.outcome_distribution:
        reasons.append("sampled outcome distribution is required")
    else:
        total = 0.0
        for key, value in record.outcome_distribution.items():
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                reasons.append(f"outcome {key!r} is not numeric")
                continue
            if numeric < 0:
                reasons.append(f"outcome {key!r} is negative")
            total += max(0.0, numeric)
        if total <= 0:
            reasons.append("outcome distribution total must be positive")
    return not reasons, tuple(reasons)


def as_qrf_run_evidence(record: GateModelExecutionRecord, *, project_id: str, experiment_id: str, algorithm: str, classical_baseline_id: str) -> QuantumRunEvidence:
    accepted, reasons = validate_gate_model_execution(record)
    if not accepted:
        raise ValueError("invalid provider-neutral QPU execution: " + "; ".join(reasons))
    return QuantumRunEvidence(
        project_id=project_id,
        experiment_id=experiment_id,
        domain=QuantumDomain.COMPUTING,
        evidence_level=EvidenceLevel.QPU_EXECUTED,
        backend=QuantumBackendRecord(
            provider=record.provider,
            backend=record.backend,
            backend_class=BackendClass.QPU,
            modality=record.modality,
            calibration_id=record.calibration_id,
            native_gate_set=record.native_gate_set,
            metadata={**record.metadata, "job_id": record.job_id},
        ),
        algorithm=algorithm,
        classical_baseline_id=classical_baseline_id,
        circuit_digest=record.canonical_program_digest,
        qasm_or_qir_digest=record.canonical_program_digest,
        shots=record.shots,
        result_digest=record.result_digest,
        outcome_distribution={str(k): float(v) for k, v in record.outcome_distribution.items()},
        notes=(f"provider_job_id={record.job_id}", f"queue_seconds={record.queue_seconds}", f"latency_seconds={record.latency_seconds}", f"cost_usd={record.cost_usd}"),
    )

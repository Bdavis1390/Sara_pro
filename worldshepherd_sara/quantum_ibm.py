"""Credential-gated IBM Quantum hardware adapter for QRF-BELL-001.

No credential is persisted by this module. A caller must inject the API key at
runtime. The returned evidence is hardware execution evidence, not a quantum
advantage claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from time import perf_counter
from typing import Any

from qiskit import QuantumCircuit, qasm3
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType


@dataclass(frozen=True)
class IBMQPUResult:
    provider: str
    backend: str
    job_id: str
    shots: int
    counts: dict[str, int]
    correlated_fraction: float
    circuit_digest: str
    transpiled_circuit_digest: str
    result_digest: str
    calibration_id: str | None
    backend_num_qubits: int | None
    native_operations: tuple[str, ...]
    executed_at_utc: str
    instance: str | None = None
    instance_plan: str | None = None
    backend_properties_digest: str | None = None
    job_metrics: dict[str, Any] | None = None
    job_metrics_digest: str | None = None
    queue_seconds: float | None = None
    platform_latency_seconds: float | None = None
    wall_latency_seconds: float | None = None
    qpu_charge_time_seconds: float | None = None
    runtime_version: str | None = None
    claim_class: str = "quantum_executed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _digest_json(payload: Any) -> str:
    return _digest_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))


def _json_safe(payload: Any) -> Any:
    return json.loads(json.dumps(payload, sort_keys=True, default=str))


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _elapsed_seconds(start: Any, end: Any) -> float | None:
    left = _parse_timestamp(start)
    right = _parse_timestamp(end)
    if left is None or right is None:
        return None
    seconds = (right - left).total_seconds()
    return max(0.0, seconds)


def _normalize_plan(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("_", "-")
    if normalized.endswith(" plan"):
        normalized = normalized[:-5].strip()
    return normalized or None


def _active_instance_identity(service: QiskitRuntimeService) -> tuple[str | None, str | None]:
    """Resolve the active IBM instance and its advertised plan without guessing."""
    try:
        active_raw = service.active_instance()
    except Exception:
        active_raw = None
    active = str(active_raw).strip() if active_raw is not None else None
    if not active:
        return None, None

    try:
        instances = service.instances()
    except Exception:
        return active, None

    for row in instances:
        if not isinstance(row, dict):
            continue
        crn = str(row.get("crn") or "").strip()
        name = str(row.get("name") or "").strip()
        if active in {crn, name}:
            plan = row.get("plan")
            return active, str(plan).strip() if plan is not None else None
    return active, None


def _build_hardware_bell_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2, name="QRF-BELL-001")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return circuit


def _properties_snapshot(job: Any, backend: Any) -> tuple[Any | None, str | None, str | None]:
    properties = None
    try:
        properties = job.properties()
    except Exception:
        try:
            properties = backend.properties()
        except Exception:
            properties = None
    if properties is None:
        return None, None, None

    try:
        payload = properties.to_dict()
    except Exception:
        payload = {"repr": repr(properties)}
    safe_payload = _json_safe(payload)
    stamp = getattr(properties, "last_update_date", None)
    return safe_payload, _digest_json(safe_payload), str(stamp) if stamp is not None else None


def _job_metrics(job: Any) -> tuple[dict[str, Any], str, float | None, float | None, float | None, str | None]:
    try:
        metrics_raw = job.metrics()
    except Exception as exc:
        metrics_raw = {"metrics_error": f"{type(exc).__name__}: {exc}"}
    metrics = _json_safe(metrics_raw)
    digest = _digest_json(metrics)
    timestamps = metrics.get("timestamps", {}) if isinstance(metrics, dict) else {}
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    queue_seconds = _elapsed_seconds(timestamps.get("created"), timestamps.get("running"))
    platform_latency = _elapsed_seconds(timestamps.get("created"), timestamps.get("finished"))
    qpu_charge = None
    if isinstance(usage, dict):
        raw_charge = usage.get("qpu_charge_time_seconds")
        if raw_charge is None:
            raw_charge = usage.get("quantum_seconds")
        if raw_charge is not None:
            try:
                qpu_charge = max(0.0, float(raw_charge))
            except (TypeError, ValueError):
                qpu_charge = None
    finished = timestamps.get("finished") if isinstance(timestamps, dict) else None
    finished_dt = _parse_timestamp(finished)
    finished_z = finished_dt.isoformat().replace("+00:00", "Z") if finished_dt else None
    return metrics, digest, queue_seconds, platform_latency, qpu_charge, finished_z


def run_bell_on_ibm_hardware(
    *,
    token: str,
    instance: str | None = None,
    backend_name: str | None = None,
    shots: int = 4096,
    optimization_level: int = 1,
    expected_plan: str | None = None,
) -> IBMQPUResult:
    if not token or not token.strip():
        raise ValueError("IBM Quantum API token must be injected at runtime")
    if shots <= 0:
        raise ValueError("shots must be positive")
    if optimization_level not in {0, 1, 2, 3}:
        raise ValueError("optimization_level must be one of 0, 1, 2, 3")

    normalized_expected_plan = _normalize_plan(expected_plan)
    service_kwargs: dict[str, Any] = {
        "channel": "ibm_quantum_platform",
        "token": token.strip(),
    }
    if instance:
        service_kwargs["instance"] = instance
    elif normalized_expected_plan:
        # Current IBM Runtime supports plan-constrained automatic instance selection.
        # This prevents an Open-Plan run from silently consuming another account plan.
        service_kwargs["plans_preference"] = [normalized_expected_plan]
    service = QiskitRuntimeService(**service_kwargs)

    if backend_name:
        backend = service.backend(backend_name)
        if getattr(backend, "simulator", False):
            raise ValueError("backend_name must identify real quantum hardware, not a simulator")
        status = backend.status()
        if not getattr(status, "operational", False):
            raise RuntimeError(f"backend {backend_name} is not operational")
    else:
        backend = service.least_busy(
            operational=True,
            simulator=False,
            min_num_qubits=2,
        )

    # Resolve and verify the active billing/access instance before submitting any QPU job.
    active_instance, actual_plan = _active_instance_identity(service)
    if active_instance is None:
        raise RuntimeError("unable to verify the active IBM Quantum instance before hardware submission")
    if actual_plan is None:
        raise RuntimeError("unable to verify the active IBM Quantum instance plan before hardware submission")
    normalized_actual_plan = _normalize_plan(actual_plan)
    if normalized_expected_plan and normalized_actual_plan != normalized_expected_plan:
        raise RuntimeError(
            f"active IBM plan {actual_plan!r} does not match expected plan {expected_plan!r}; refusing QPU submission"
        )

    circuit = _build_hardware_bell_circuit()
    source_qasm = qasm3.dumps(circuit)
    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=optimization_level,
    )
    isa_circuit = pass_manager.run(circuit)
    isa_qasm = qasm3.dumps(isa_circuit)

    # A Backend passed as SamplerV2 mode is IBM Runtime job mode, which is valid for Open Plan.
    sampler = SamplerV2(mode=backend)
    wall_start = perf_counter()
    job = sampler.run([isa_circuit], shots=shots)
    primitive_result = job.result()
    wall_latency = max(0.0, perf_counter() - wall_start)

    counts_raw = primitive_result[0].data.meas.get_counts()
    counts = {str(key): int(value) for key, value in counts_raw.items()}
    correlated = (counts.get("00", 0) + counts.get("11", 0)) / shots

    result_payload = {
        "provider": "IBM Quantum Platform",
        "instance": active_instance,
        "instance_plan": actual_plan,
        "backend": str(getattr(backend, "name", backend_name or "unknown")),
        "job_id": str(job.job_id()),
        "shots": shots,
        "counts": dict(sorted(counts.items())),
    }
    result_digest = _digest_json(result_payload)
    _, properties_digest, calibration_id = _properties_snapshot(job, backend)
    metrics, metrics_digest, queue_seconds, platform_latency, qpu_charge, finished_z = _job_metrics(job)

    operations = tuple(sorted(str(op) for op in getattr(backend, "operation_names", ())))
    num_qubits = getattr(backend, "num_qubits", None)
    return IBMQPUResult(
        provider=result_payload["provider"],
        backend=result_payload["backend"],
        job_id=result_payload["job_id"],
        shots=shots,
        counts=dict(sorted(counts.items())),
        correlated_fraction=correlated,
        circuit_digest=_digest_text(source_qasm),
        transpiled_circuit_digest=_digest_text(isa_qasm),
        result_digest=result_digest,
        calibration_id=calibration_id,
        backend_num_qubits=int(num_qubits) if num_qubits is not None else None,
        native_operations=operations,
        executed_at_utc=finished_z or _utc_now_z(),
        instance=active_instance,
        instance_plan=actual_plan,
        backend_properties_digest=properties_digest,
        job_metrics=metrics,
        job_metrics_digest=metrics_digest,
        queue_seconds=queue_seconds,
        platform_latency_seconds=platform_latency,
        wall_latency_seconds=wall_latency,
        qpu_charge_time_seconds=qpu_charge,
        runtime_version=importlib.metadata.version("qiskit-ibm-runtime"),
    )


def build_sara_qpu_external_evidence(
    result: IBMQPUResult,
    *,
    plan_name: str | None,
    cost_usd: float,
    campaign_gate_id: str = "SARA-QRF-EXT-01",
) -> ExternalEvidenceRecord:
    """Convert a successful IBM hardware result into a gate-bound SARA intake record.

    The execution plan and instance must be verified by the service before submission.
    ``plan_name`` is treated only as the caller's expected plan and must match the
    service-resolved plan. For an IBM Open Plan execution, cost can be 0.0; paid-plan
    executions should pass the actual recorded/allocated execution cost.
    """
    if not result.instance:
        raise ValueError("verified IBM instance identity is required for external QPU evidence")
    if not result.instance_plan:
        raise ValueError("verified IBM instance plan is required for external QPU evidence")
    actual_plan = _normalize_plan(result.instance_plan)
    expected_plan = _normalize_plan(plan_name)
    if expected_plan and actual_plan != expected_plan:
        raise ValueError(
            f"recorded IBM plan {result.instance_plan!r} does not match expected plan {plan_name!r}"
        )
    if cost_usd < 0:
        raise ValueError("cost_usd must be non-negative")
    if not result.backend_properties_digest:
        raise ValueError("IBM job/backend properties digest is required for SARA-QRF-EXT-01")
    if result.queue_seconds is None:
        raise ValueError("IBM job metrics must expose created/running timestamps for measured queue time")
    latency = result.platform_latency_seconds
    if latency is None:
        latency = result.wall_latency_seconds
    if latency is None:
        raise ValueError("measured end-to-end IBM job latency is required")

    raw_payload = result.to_dict()
    raw_artifact_digest = _digest_json(raw_payload)
    configuration_digest = _digest_json({
        "instance": result.instance,
        "instance_plan": result.instance_plan,
        "backend": result.backend,
        "shots": result.shots,
        "circuit_digest": result.circuit_digest,
        "transpiled_circuit_digest": result.transpiled_circuit_digest,
        "runtime_version": result.runtime_version,
    })
    protocol_digest = _digest_text(
        "QRF-BELL-001 IBM hardware protocol v1.1: resolve and verify active instance/plan before submission; "
        "transpile to named backend; execute measured Bell circuit in job mode; retain backend properties, runtime metrics, "
        "result counts, latency, queue, cost, instance identity, plan identity, and immutable digests."
    )

    return ExternalEvidenceRecord(
        project_id="SARA-QRF",
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id=f"ibm-quantum-platform:{result.job_id}",
        raw_artifact_digest=raw_artifact_digest,
        collected_utc=result.executed_at_utc,
        provider_or_lab=result.provider,
        configuration_digest=configuration_digest,
        repeat_count=1,
        calibration_id=result.calibration_id,
        result_digest=result.result_digest,
        job_or_run_id=result.job_id,
        backend_or_device=result.backend,
        latency_seconds=float(latency),
        cost_usd=float(cost_usd),
        environment="remote_cloud_qpu",
        metadata={
            "campaign_gate_id": campaign_gate_id,
            "test_protocol_digest": protocol_digest,
            "program_digest": result.circuit_digest,
            "transpiled_program_digest": result.transpiled_circuit_digest,
            "backend_properties_digest": result.backend_properties_digest,
            "queue_seconds": str(result.queue_seconds),
            "failure_mode": "none_observed",
            "instance": result.instance,
            "plan_name": result.instance_plan,
            "plan_verification": "service_resolved_before_submission",
            "job_metrics_digest": result.job_metrics_digest or "unavailable",
            "qpu_charge_time_seconds": "unavailable" if result.qpu_charge_time_seconds is None else str(result.qpu_charge_time_seconds),
            "runtime_version": result.runtime_version or "unknown",
            "wall_latency_seconds": "unavailable" if result.wall_latency_seconds is None else str(result.wall_latency_seconds),
        },
    )

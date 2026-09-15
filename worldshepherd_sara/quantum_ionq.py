"""Credential-gated IonQ Quantum Cloud v0.4 adapter for QRF-BELL-001.

The API key is runtime-only. Simulator backends are rejected for hardware evidence.
The adapter retains provider job, backend, timing, cost, backend snapshot, program,
result, and normalized distribution identities for provider-neutral reproduction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from time import monotonic, sleep
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from worldshepherd_sara.quantum_external_evidence import ExternalEvidenceRecord, ExternalEvidenceType
from worldshepherd_sara.quantum_provider import GateModelExecutionRecord

API_BASE = "https://api.ionq.co/v0.4"


def _digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def _utc_z(value: str | None = None) -> str:
    if value:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _seconds(start: str | None, end: str | None) -> float:
    if not start or not end:
        return 0.0
    a = datetime.fromisoformat(start.replace("Z", "+00:00"))
    b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return max(0.0, (b - a).total_seconds())


def bell_payload(*, backend: str, shots: int) -> dict[str, Any]:
    if not backend.startswith("qpu."):
        raise ValueError("IonQ hardware evidence requires an explicit qpu.* backend")
    if shots <= 0:
        raise ValueError("shots must be positive")
    return {
        "type": "ionq.circuit.v1",
        "name": "QRF-BELL-001",
        "shots": int(shots),
        "backend": backend,
        "metadata": {"worldshepherd_benchmark": "QRF-BELL-001"},
        "input": {
            "qubits": 2,
            "gateset": "qis",
            "circuit": [
                {"gate": "h", "target": 0},
                {"gate": "cnot", "control": 0, "target": 1},
            ],
        },
    }


def _request_json(token: str, method: str, path: str, payload: Any | None = None) -> Any:
    if not token.strip():
        raise ValueError("IonQ API key must be injected at runtime")
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        API_BASE + path,
        data=body,
        method=method,
        headers={"Authorization": f"apiKey {token.strip()}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"IonQ API HTTP {exc.code}: {detail[:1000]}") from exc
    except URLError as exc:
        raise RuntimeError(f"IonQ API transport error: {exc}") from exc


def _probability_bits(probabilities: dict[str, Any], qubits: int = 2) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, raw in probabilities.items():
        index = int(str(key))
        out[format(index, f"0{qubits}b")] = float(raw)
    total = sum(out.values())
    if total <= 0:
        raise ValueError("IonQ probability result is empty or non-positive")
    return {key: value / total for key, value in sorted(out.items())}


@dataclass(frozen=True)
class IonQQPUResult:
    provider: str
    backend: str
    job_id: str
    shots: int
    probabilities: dict[str, float]
    program_digest: str
    compiled_program_digest: str
    result_digest: str
    raw_artifact_digest: str
    configuration_digest: str
    backend_properties_digest: str
    calibration_id: str | None
    submitted_at: str
    started_at: str
    completed_at: str
    queue_seconds: float
    latency_seconds: float
    execution_duration_seconds: float
    cost_usd: float
    project_id: str | None
    stats: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def provider_record(self) -> GateModelExecutionRecord:
        return GateModelExecutionRecord(
            provider=self.provider,
            backend=self.backend,
            modality="trapped_ion_gate_model",
            job_id=self.job_id,
            collected_utc=self.completed_at,
            shots=self.shots,
            canonical_program_digest=self.program_digest,
            compiled_program_digest=self.compiled_program_digest,
            result_digest=self.result_digest,
            configuration_digest=self.configuration_digest,
            raw_artifact_digest=self.raw_artifact_digest,
            outcome_distribution=self.probabilities,
            queue_seconds=self.queue_seconds,
            latency_seconds=self.latency_seconds,
            cost_usd=self.cost_usd,
            calibration_id=self.calibration_id,
            backend_properties_digest=self.backend_properties_digest,
            metadata={"project_id": self.project_id or "unknown", "simulator": "false"},
        )


def run_bell_on_ionq_hardware(
    *,
    token: str,
    backend: str,
    shots: int = 4096,
    poll_seconds: float = 5.0,
    timeout_seconds: float = 1800.0,
    request_json: Callable[[str, str, str, Any | None], Any] = _request_json,
) -> IonQQPUResult:
    payload = bell_payload(backend=backend, shots=shots)
    created = request_json(token, "POST", "/jobs", payload)
    job_id = str(created.get("id", "")).strip()
    if not job_id:
        raise RuntimeError("IonQ create-job response did not include a job ID")

    deadline = monotonic() + timeout_seconds
    job: dict[str, Any] = {}
    while monotonic() < deadline:
        job = dict(request_json(token, "GET", f"/jobs/{job_id}", None))
        status = str(job.get("status", ""))
        if status == "completed":
            break
        if status in {"failed", "canceled"}:
            raise RuntimeError(f"IonQ job {job_id} ended with status {status}: {job.get('failure')}")
        sleep(max(0.1, poll_seconds))
    else:
        raise TimeoutError(f"IonQ job {job_id} did not complete before timeout")

    actual_backend = str(job.get("backend", ""))
    if actual_backend != backend or not actual_backend.startswith("qpu.") or bool(job.get("dry_run")):
        raise RuntimeError("IonQ completed record does not prove execution on the requested real QPU backend")

    probabilities_raw = request_json(token, "GET", f"/jobs/{job_id}/results/probabilities", None)
    probabilities = _probability_bits(dict(probabilities_raw), 2)
    cost_payload = request_json(token, "GET", f"/jobs/{job_id}/cost", None)
    backend_payload = request_json(token, "GET", f"/backends/{backend}", None)

    actual_cost = cost_payload.get("actual_cost")
    if actual_cost is None:
        actual_cost = cost_payload.get("estimated_cost", 0.0)
    cost_usd = max(0.0, float(actual_cost))

    submitted = _utc_z(str(job.get("submitted_at")))
    started = _utc_z(str(job.get("started_at") or job.get("submitted_at")))
    completed = _utc_z(str(job.get("completed_at") or job.get("submitted_at")))
    stats = dict(job.get("stats") or {})
    execution_ms = job.get("execution_duration_ms")
    execution_seconds = max(0.0, float(execution_ms or 0.0) / 1000.0)

    compilation = (job.get("output") or {}).get("compilation") or {}
    program_digest = _digest(payload["input"])
    compiled_program_digest = _digest(compilation if compilation else payload["input"])
    result_digest = _digest({"job_id": job_id, "backend": backend, "shots": shots, "probabilities": probabilities})
    configuration_digest = _digest({"backend": backend, "shots": shots, "type": payload["type"], "settings": job.get("settings") or {}})
    backend_properties_digest = _digest(backend_payload)
    calibration_id = backend_payload.get("characterization_id") if isinstance(backend_payload, dict) else None

    raw = {"job": job, "probabilities": probabilities_raw, "cost": cost_payload, "backend": backend_payload}
    return IonQQPUResult(
        provider="IonQ Quantum Cloud",
        backend=backend,
        job_id=job_id,
        shots=shots,
        probabilities=probabilities,
        program_digest=program_digest,
        compiled_program_digest=compiled_program_digest,
        result_digest=result_digest,
        raw_artifact_digest=_digest(raw),
        configuration_digest=configuration_digest,
        backend_properties_digest=backend_properties_digest,
        calibration_id=None if calibration_id is None else str(calibration_id),
        submitted_at=submitted,
        started_at=started,
        completed_at=completed,
        queue_seconds=_seconds(submitted, started),
        latency_seconds=_seconds(submitted, completed),
        execution_duration_seconds=execution_seconds,
        cost_usd=cost_usd,
        project_id=None if job.get("project_id") is None else str(job.get("project_id")),
        stats=stats,
    )


def build_sara_qpu_external_evidence(result: IonQQPUResult, *, campaign_gate_id: str = "SARA-QRF-EXT-01") -> ExternalEvidenceRecord:
    protocol_digest = _digest({"protocol": "QRF-BELL-001 IonQ hardware protocol v1.0", "api": "v0.4"})
    return ExternalEvidenceRecord(
        project_id="SARA-QRF",
        evidence_type=ExternalEvidenceType.QPU_EXECUTION,
        source_id=f"ionq-quantum-cloud:{result.job_id}",
        raw_artifact_digest=result.raw_artifact_digest,
        collected_utc=result.completed_at,
        provider_or_lab=result.provider,
        configuration_digest=result.configuration_digest,
        repeat_count=1,
        calibration_id=result.calibration_id,
        result_digest=result.result_digest,
        job_or_run_id=result.job_id,
        backend_or_device=result.backend,
        latency_seconds=result.latency_seconds,
        cost_usd=result.cost_usd,
        environment="remote_cloud_qpu",
        metadata={
            "campaign_gate_id": campaign_gate_id,
            "test_protocol_digest": protocol_digest,
            "program_digest": result.program_digest,
            "transpiled_program_digest": result.compiled_program_digest,
            "backend_properties_digest": result.backend_properties_digest,
            "queue_seconds": str(result.queue_seconds),
            "failure_mode": "none_observed",
            "provider_project_id": result.project_id or "unknown",
            "execution_duration_seconds": str(result.execution_duration_seconds),
        },
    )

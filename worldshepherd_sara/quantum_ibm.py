"""Credential-gated IBM Quantum hardware adapter for QRF-BELL-001.

No credential is persisted by this module. A caller must inject the API token at
runtime. The returned evidence is hardware execution evidence, not a quantum
advantage claim.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any

from qiskit import QuantumCircuit, qasm3
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


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
    claim_class: str = "quantum_executed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _build_hardware_bell_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2, name="QRF-BELL-001")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return circuit


def _calibration_id(backend: Any) -> str | None:
    try:
        properties = backend.properties()
    except Exception:
        return None
    if properties is None:
        return None
    stamp = getattr(properties, "last_update_date", None)
    return str(stamp) if stamp is not None else None


def run_bell_on_ibm_hardware(
    *,
    token: str,
    instance: str | None = None,
    backend_name: str | None = None,
    shots: int = 4096,
    optimization_level: int = 1,
) -> IBMQPUResult:
    if not token or not token.strip():
        raise ValueError("IBM Quantum API token must be injected at runtime")
    if shots <= 0:
        raise ValueError("shots must be positive")
    if optimization_level not in {0, 1, 2, 3}:
        raise ValueError("optimization_level must be one of 0, 1, 2, 3")

    service_kwargs: dict[str, str] = {
        "channel": "ibm_quantum_platform",
        "token": token.strip(),
    }
    if instance:
        service_kwargs["instance"] = instance
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

    circuit = _build_hardware_bell_circuit()
    source_qasm = qasm3.dumps(circuit)
    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=optimization_level,
    )
    isa_circuit = pass_manager.run(circuit)
    isa_qasm = qasm3.dumps(isa_circuit)

    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa_circuit], shots=shots)
    primitive_result = job.result()
    counts_raw = primitive_result[0].data.meas.get_counts()
    counts = {str(key): int(value) for key, value in counts_raw.items()}
    correlated = (counts.get("00", 0) + counts.get("11", 0)) / shots

    result_payload = {
        "provider": "IBM Quantum Platform",
        "backend": str(getattr(backend, "name", backend_name or "unknown")),
        "job_id": str(job.job_id()),
        "shots": shots,
        "counts": dict(sorted(counts.items())),
    }
    result_digest = _digest_text(
        json.dumps(result_payload, sort_keys=True, separators=(",", ":"))
    )

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
        calibration_id=_calibration_id(backend),
        backend_num_qubits=int(num_qubits) if num_qubits is not None else None,
        native_operations=operations,
        executed_at_utc=datetime.now(timezone.utc).isoformat(),
    )

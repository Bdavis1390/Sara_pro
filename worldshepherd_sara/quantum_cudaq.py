"""Provider-neutral CUDA-Q portable execution adapter for Worldshepherd QRF.

CUDA-Q is used here as a portable CPU/GPU/QPU programming layer. A CUDA-Q run is
*not* accepted as hardware evidence solely because a hardware-capable target name was
selected. Provider-specific job/device provenance must still be captured by an IBM,
Braket, or future direct-provider evidence adapter before QRF can classify the run as
external-QPU evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import importlib
import importlib.metadata
import json
from time import perf_counter
from typing import Any, Mapping


_CANONICAL_BELL_SPEC = {
    "benchmark_id": "QRF-BELL-001",
    "qubits": 2,
    "operations": ["H q0", "CX q0 q1", "MZ q0 q1"],
    "expected_ideal_support": ["00", "11"],
}


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def canonical_cudaq_bell_digest() -> str:
    return _digest_json(_CANONICAL_BELL_SPEC)


def _json_safe(payload: Any) -> Any:
    return json.loads(json.dumps(payload, sort_keys=True, default=str))


def _counts_dict(result: Any) -> dict[str, int]:
    try:
        items = result.items()
    except AttributeError:
        try:
            return {str(key): int(value) for key, value in dict(result).items()}
        except Exception as exc:
            raise TypeError("CUDA-Q sample result could not be converted to counts") from exc
    return {str(key): int(value) for key, value in items}


@dataclass(frozen=True)
class CudaQPortableRun:
    benchmark_id: str
    canonical_program_digest: str
    requested_target: str
    resolved_target: str
    target_options: Mapping[str, Any]
    shots: int
    counts: Mapping[str, int]
    correlated_fraction: float
    result_digest: str
    wall_latency_seconds: float
    cudaq_version: str | None
    evidence_class: str = "portable_execution_unverified_hardware_provenance"
    claim_control: str = (
        "CUDA-Q portable execution evidence only. Even when a hardware-capable CUDA-Q target is requested, this record is not external-QPU evidence "
        "until a provider-specific adapter retains immutable job/device/backend/calibration/cost/latency provenance."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_bell_cudaq(
    *,
    target: str = "qpp-cpu",
    shots: int = 1000,
    target_options: Mapping[str, Any] | None = None,
) -> CudaQPortableRun:
    """Run the frozen two-qubit Bell workload through a selected CUDA-Q target.

    This function is deliberately portable rather than provider-evidentiary. For
    example, IonQ/Quantinuum targets can be configured here, but a hardware run must
    later be paired with provider-specific job identity before QRF promotion.
    """
    if not target.strip():
        raise ValueError("CUDA-Q target is required")
    if shots <= 0:
        raise ValueError("shots must be positive")
    options = dict(target_options or {})
    if options.get("emulate") is True:
        # Preserve an explicit marker; emulation can never be mistaken for hardware.
        options["emulate"] = True

    cudaq = importlib.import_module("cudaq")
    cudaq.set_target(target, **options)
    resolved_target = str(getattr(cudaq.get_target(), "name", target))

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(2)
    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.mz(qubits)

    wall_start = perf_counter()
    result = cudaq.sample(kernel, shots_count=shots)
    wall_latency = max(0.0, perf_counter() - wall_start)
    counts = _counts_dict(result)
    if not counts:
        raise RuntimeError("CUDA-Q returned no samples")
    total = sum(counts.values())
    if total <= 0:
        raise RuntimeError("CUDA-Q sample counts have zero total")
    correlated = (counts.get("00", 0) + counts.get("11", 0)) / total

    try:
        version = importlib.metadata.version("cudaq")
    except importlib.metadata.PackageNotFoundError:
        version = None
    payload = {
        "benchmark_id": "QRF-BELL-001",
        "canonical_program_digest": canonical_cudaq_bell_digest(),
        "requested_target": target,
        "resolved_target": resolved_target,
        "target_options": _json_safe(options),
        "shots": shots,
        "counts": dict(sorted(counts.items())),
    }
    return CudaQPortableRun(
        benchmark_id="QRF-BELL-001",
        canonical_program_digest=payload["canonical_program_digest"],
        requested_target=target,
        resolved_target=resolved_target,
        target_options=_json_safe(options),
        shots=shots,
        counts=dict(sorted(counts.items())),
        correlated_fraction=correlated,
        result_digest=_digest_json(payload),
        wall_latency_seconds=wall_latency,
        cudaq_version=version,
    )

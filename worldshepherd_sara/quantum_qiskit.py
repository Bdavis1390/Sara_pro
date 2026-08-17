"""Optional Qiskit/Aer execution adapter for the Quantum Readiness Fabric.

This module is deliberately separate from the dependency-free governance core.
Importing ``worldshepherd_sara.quantum_readiness`` never requires Qiskit.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


@dataclass(frozen=True)
class BellSimulationResult:
    backend: str
    noisy: bool
    shots: int
    seed: int
    counts: Mapping[str, int]
    correlated_fraction: float
    result_digest: str
    noise_model: Mapping[str, float]


def build_bell_circuit() -> QuantumCircuit:
    circuit = QuantumCircuit(2, 2, name="QRF-BELL-001")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    return circuit


def _noise_model(one_qubit_error: float, two_qubit_error: float) -> NoiseModel:
    model = NoiseModel()
    model.add_all_qubit_quantum_error(
        depolarizing_error(one_qubit_error, 1), ["h"]
    )
    model.add_all_qubit_quantum_error(
        depolarizing_error(two_qubit_error, 2), ["cx"]
    )
    return model


def run_bell_simulation(
    *,
    shots: int = 4096,
    seed: int = 9675,
    noisy: bool = False,
    one_qubit_error: float = 0.02,
    two_qubit_error: float = 0.08,
) -> BellSimulationResult:
    if shots <= 0:
        raise ValueError("shots must be positive")
    if not 0 <= one_qubit_error <= 1:
        raise ValueError("one_qubit_error must be in [0, 1]")
    if not 0 <= two_qubit_error <= 1:
        raise ValueError("two_qubit_error must be in [0, 1]")

    circuit = build_bell_circuit()
    noise = _noise_model(one_qubit_error, two_qubit_error) if noisy else None
    backend = AerSimulator(noise_model=noise)
    job = backend.run(circuit, shots=shots, seed_simulator=seed)
    counts = {str(k): int(v) for k, v in job.result().get_counts(circuit).items()}
    correlated = (counts.get("00", 0) + counts.get("11", 0)) / shots

    payload = {
        "backend": "qiskit_aer.AerSimulator",
        "noisy": noisy,
        "shots": shots,
        "seed": seed,
        "counts": dict(sorted(counts.items())),
        "noise_model": {
            "one_qubit_depolarizing": one_qubit_error if noisy else 0.0,
            "two_qubit_depolarizing": two_qubit_error if noisy else 0.0,
        },
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return BellSimulationResult(
        backend=payload["backend"],
        noisy=noisy,
        shots=shots,
        seed=seed,
        counts=counts,
        correlated_fraction=correlated,
        result_digest=f"sha256:{digest}",
        noise_model=payload["noise_model"],
    )

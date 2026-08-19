"""Small-Hamiltonian quantum-materials benchmark harness for Worldshepherd.

This closes the software path for exact-reference versus variational-state
comparison. It is not an Al-Ti result until a physically specified, provenance-
controlled Hamiltonian derived from an actual structure is supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import cos, pi, sin
from typing import Mapping

import numpy as np
from qiskit.quantum_info import SparsePauliOp, Statevector


@dataclass(frozen=True)
class MaterialsBenchmarkResult:
    benchmark_id: str
    qubits: int
    exact_ground_energy: float
    variational_best_energy: float
    absolute_energy_error: float
    parameter_points_evaluated: int
    hamiltonian_digest: str
    evidence_level: str
    mission_use_decision: str
    claim_control: str


def build_hamiltonian(pauli_terms: Mapping[str, float]) -> SparsePauliOp:
    if not pauli_terms:
        raise ValueError("at least one Pauli term is required")
    lengths = {len(label) for label in pauli_terms}
    if len(lengths) != 1 or next(iter(lengths)) <= 0:
        raise ValueError("all Pauli labels must have the same positive length")
    if any(set(label) - set("IXYZ") for label in pauli_terms):
        raise ValueError("Pauli labels may contain only I/X/Y/Z")
    return SparsePauliOp.from_list([(label, float(coeff)) for label, coeff in pauli_terms.items()])


def _digest_terms(pauli_terms: Mapping[str, float]) -> str:
    payload = json.dumps(dict(sorted(pauli_terms.items())), sort_keys=True, separators=(",", ":"))
    return "sha256:" + sha256(payload.encode()).hexdigest()


def exact_ground_energy(hamiltonian: SparsePauliOp) -> float:
    eigenvalues = np.linalg.eigvalsh(hamiltonian.to_matrix())
    return float(np.min(np.real(eigenvalues)))


def _product_ry_state(thetas: tuple[float, ...]) -> Statevector:
    # Little-endian tensor convention does not affect the variational minimum.
    vector = np.array([1.0 + 0.0j])
    for theta in reversed(thetas):
        qubit = np.array([cos(theta / 2.0), sin(theta / 2.0)], dtype=complex)
        vector = np.kron(vector, qubit)
    return Statevector(vector)


def variational_product_state_search(
    hamiltonian: SparsePauliOp,
    *,
    grid_points: int = 25,
) -> tuple[float, int]:
    if grid_points < 3:
        raise ValueError("grid_points must be >= 3")
    qubits = hamiltonian.num_qubits
    if qubits > 4:
        raise ValueError("grid product-state search is intentionally bounded to <=4 qubits")

    angles = np.linspace(0.0, 2.0 * pi, grid_points, endpoint=False)
    best = float("inf")
    evaluated = 0

    def walk(prefix: tuple[float, ...]) -> None:
        nonlocal best, evaluated
        if len(prefix) == qubits:
            state = _product_ry_state(prefix)
            energy = float(np.real(state.expectation_value(hamiltonian)))
            evaluated += 1
            if energy < best:
                best = energy
            return
        for theta in angles:
            walk(prefix + (float(theta),))

    walk(())
    return best, evaluated


def run_materials_benchmark(
    pauli_terms: Mapping[str, float],
    *,
    benchmark_id: str,
    grid_points: int = 25,
) -> MaterialsBenchmarkResult:
    hamiltonian = build_hamiltonian(pauli_terms)
    exact = exact_ground_energy(hamiltonian)
    variational, evaluated = variational_product_state_search(hamiltonian, grid_points=grid_points)
    return MaterialsBenchmarkResult(
        benchmark_id=benchmark_id,
        qubits=hamiltonian.num_qubits,
        exact_ground_energy=exact,
        variational_best_energy=variational,
        absolute_energy_error=abs(variational - exact),
        parameter_points_evaluated=evaluated,
        hamiltonian_digest=_digest_terms(pauli_terms),
        evidence_level="software_pipeline_reference_hamiltonian",
        mission_use_decision="NO_GO_BELOW_97_UNTIL_PHYSICAL_STRUCTURE_AND_CLASSICAL_REFERENCE_INGESTED",
        claim_control=(
            "This benchmark validates the exact/variational software pipeline only. It is not a WS-AlTi materials result "
            "unless the Hamiltonian is derived from a physically specified structure with retained basis/active-space provenance."
        ),
    )

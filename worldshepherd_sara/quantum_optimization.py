"""Executable quantum-vs-classical optimization benchmarks for QRF.

The canonical instances in this module are deliberately small, frozen surrogate
problems. They validate the benchmark/evidence pipeline; they are not calibrated
metasurface electromagnetic models or operational logistics mission instances.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from math import pi
from typing import Mapping

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


@dataclass(frozen=True)
class BinaryQuadraticProblem:
    problem_id: str
    project: str
    description: str
    linear: tuple[float, ...]
    quadratic: Mapping[tuple[int, int], float]
    constant: float = 0.0
    feasibility_rule: str = "always"

    @property
    def n(self) -> int:
        return len(self.linear)

    def objective(self, bits: tuple[int, ...]) -> float:
        if len(bits) != self.n or any(bit not in (0, 1) for bit in bits):
            raise ValueError("bits must be a binary tuple matching problem size")
        value = self.constant + sum(a * bits[i] for i, a in enumerate(self.linear))
        value += sum(weight * bits[i] * bits[j] for (i, j), weight in self.quadratic.items())
        return float(value)

    def feasible(self, bits: tuple[int, ...]) -> bool:
        if self.feasibility_rule == "always":
            return True
        if self.feasibility_rule == "exactly_one":
            return sum(bits) == 1
        raise ValueError(f"unsupported feasibility rule: {self.feasibility_rule}")


@dataclass(frozen=True)
class QAOABenchmarkResult:
    benchmark_id: str
    project: str
    evidence_level: str
    instance_kind: str
    problem_id: str
    qubits: int
    exact_optimum: float
    exact_optimal_bitstrings: tuple[str, ...]
    classical_states_evaluated: int
    grid_size: int
    best_gamma: float
    best_beta: float
    ideal_expected_objective: float
    ideal_optimal_probability: float
    ideal_sample_best_objective: float
    ideal_sample_feasibility_rate: float
    noisy_sample_best_objective: float
    noisy_sample_feasibility_rate: float
    noisy_optimal_probability: float
    shots: int
    seed: int
    one_qubit_error: float
    two_qubit_error: float
    promotion_decision: str
    claim_control: str
    result_digest: str


def _bits_from_index(index: int, n: int) -> tuple[int, ...]:
    return tuple((index >> qubit) & 1 for qubit in range(n))


def _display_bits(bits: tuple[int, ...]) -> str:
    return "".join(str(bit) for bit in bits)


def exact_solve(problem: BinaryQuadraticProblem) -> tuple[float, tuple[tuple[int, ...], ...]]:
    values = []
    for index in range(1 << problem.n):
        bits = _bits_from_index(index, problem.n)
        values.append((bits, problem.objective(bits)))
    optimum = min(value for _, value in values)
    states = tuple(bits for bits, value in values if abs(value - optimum) <= 1e-12)
    return optimum, states


def _qubo_to_ising(problem: BinaryQuadraticProblem) -> tuple[float, tuple[float, ...], dict[tuple[int, int], float]]:
    constant = float(problem.constant)
    linear_z = [0.0] * problem.n
    quadratic_z: dict[tuple[int, int], float] = {}

    for i, coefficient in enumerate(problem.linear):
        constant += coefficient / 2.0
        linear_z[i] -= coefficient / 2.0

    for (i, j), coefficient in problem.quadratic.items():
        if i == j or not (0 <= i < problem.n and 0 <= j < problem.n):
            raise ValueError("quadratic terms must reference two distinct valid variables")
        if j < i:
            i, j = j, i
        constant += coefficient / 4.0
        linear_z[i] -= coefficient / 4.0
        linear_z[j] -= coefficient / 4.0
        quadratic_z[(i, j)] = quadratic_z.get((i, j), 0.0) + coefficient / 4.0

    return constant, tuple(linear_z), quadratic_z


def build_qaoa_p1_circuit(problem: BinaryQuadraticProblem, gamma: float, beta: float, *, measure: bool = False) -> QuantumCircuit:
    _, linear_z, quadratic_z = _qubo_to_ising(problem)
    circuit = QuantumCircuit(problem.n, problem.n if measure else 0, name=f"{problem.problem_id}-P1")
    circuit.h(range(problem.n))

    for qubit, coefficient in enumerate(linear_z):
        if coefficient:
            circuit.rz(2.0 * gamma * coefficient, qubit)

    # exp(-i gamma J ZiZj) using CX-RZ-CX, keeping the noisy gate model explicit.
    for (i, j), coefficient in sorted(quadratic_z.items()):
        if coefficient:
            circuit.cx(i, j)
            circuit.rz(2.0 * gamma * coefficient, j)
            circuit.cx(i, j)

    for qubit in range(problem.n):
        circuit.rx(2.0 * beta, qubit)

    if measure:
        circuit.measure(range(problem.n), range(problem.n))
    return circuit


def _statevector_metrics(problem: BinaryQuadraticProblem, gamma: float, beta: float) -> tuple[float, float]:
    circuit = build_qaoa_p1_circuit(problem, gamma, beta, measure=False)
    probabilities = Statevector.from_instruction(circuit).probabilities()
    optimum, optimal_states = exact_solve(problem)
    optimal_indices = {
        sum(bit << qubit for qubit, bit in enumerate(bits)) for bits in optimal_states
    }
    expectation = 0.0
    optimal_probability = 0.0
    for index, probability in enumerate(probabilities):
        bits = _bits_from_index(index, problem.n)
        expectation += float(probability) * problem.objective(bits)
        if index in optimal_indices:
            optimal_probability += float(probability)
    return expectation, optimal_probability


def optimize_qaoa_p1(problem: BinaryQuadraticProblem, *, grid_size: int = 17) -> tuple[float, float, float, float]:
    if grid_size < 3:
        raise ValueError("grid_size must be >= 3")
    best: tuple[float, float, float, float] | None = None
    for gamma in np.linspace(0.0, pi, grid_size, endpoint=False):
        for beta in np.linspace(0.0, pi / 2.0, grid_size, endpoint=False):
            expectation, optimal_probability = _statevector_metrics(problem, float(gamma), float(beta))
            candidate = (expectation, -optimal_probability, float(gamma), float(beta))
            if best is None or candidate < best:
                best = candidate
    assert best is not None
    expectation, neg_optimal_probability, gamma, beta = best
    return gamma, beta, expectation, -neg_optimal_probability


def _noise_model(one_qubit_error: float, two_qubit_error: float) -> NoiseModel:
    if not 0 <= one_qubit_error <= 1 or not 0 <= two_qubit_error <= 1:
        raise ValueError("noise probabilities must be in [0, 1]")
    model = NoiseModel()
    one = depolarizing_error(one_qubit_error, 1)
    two = depolarizing_error(two_qubit_error, 2)
    for gate in ("h", "rz", "rx"):
        model.add_all_qubit_quantum_error(one, [gate])
    model.add_all_qubit_quantum_error(two, ["cx"])
    return model


def _counts_metrics(
    problem: BinaryQuadraticProblem,
    counts: Mapping[str, int],
    *,
    shots: int,
    optimum: float,
) -> tuple[float, float, float]:
    best_objective = float("inf")
    feasible = 0
    optimal = 0
    for key, count in counts.items():
        cleaned = key.replace(" ", "")
        bits = tuple(int(bit) for bit in reversed(cleaned))
        value = problem.objective(bits)
        best_objective = min(best_objective, value)
        if problem.feasible(bits):
            feasible += int(count)
        if abs(value - optimum) <= 1e-12:
            optimal += int(count)
    return best_objective, feasible / shots, optimal / shots


def _sample(
    problem: BinaryQuadraticProblem,
    gamma: float,
    beta: float,
    *,
    shots: int,
    seed: int,
    noise_model: NoiseModel | None,
) -> Mapping[str, int]:
    circuit = build_qaoa_p1_circuit(problem, gamma, beta, measure=True)
    backend = AerSimulator(noise_model=noise_model)
    result = backend.run(circuit, shots=shots, seed_simulator=seed).result()
    return {str(key): int(value) for key, value in result.get_counts(circuit).items()}


def run_benchmark(
    problem: BinaryQuadraticProblem,
    *,
    benchmark_id: str,
    instance_kind: str,
    grid_size: int = 17,
    shots: int = 4096,
    seed: int = 9675,
    one_qubit_error: float = 0.005,
    two_qubit_error: float = 0.02,
) -> QAOABenchmarkResult:
    if shots <= 0:
        raise ValueError("shots must be positive")
    optimum, optimal_states = exact_solve(problem)
    gamma, beta, expectation, ideal_optimal_probability = optimize_qaoa_p1(problem, grid_size=grid_size)

    ideal_counts = _sample(problem, gamma, beta, shots=shots, seed=seed, noise_model=None)
    noisy_counts = _sample(
        problem,
        gamma,
        beta,
        shots=shots,
        seed=seed,
        noise_model=_noise_model(one_qubit_error, two_qubit_error),
    )
    ideal_best, ideal_feasible, _ = _counts_metrics(problem, ideal_counts, shots=shots, optimum=optimum)
    noisy_best, noisy_feasible, noisy_optimal = _counts_metrics(problem, noisy_counts, shots=shots, optimum=optimum)

    payload = {
        "benchmark_id": benchmark_id,
        "project": problem.project,
        "evidence_level": "ideal_and_noisy_simulation",
        "instance_kind": instance_kind,
        "problem_id": problem.problem_id,
        "qubits": problem.n,
        "exact_optimum": optimum,
        "exact_optimal_bitstrings": tuple(_display_bits(bits) for bits in optimal_states),
        "classical_states_evaluated": 1 << problem.n,
        "grid_size": grid_size,
        "best_gamma": gamma,
        "best_beta": beta,
        "ideal_expected_objective": expectation,
        "ideal_optimal_probability": ideal_optimal_probability,
        "ideal_sample_best_objective": ideal_best,
        "ideal_sample_feasibility_rate": ideal_feasible,
        "noisy_sample_best_objective": noisy_best,
        "noisy_sample_feasibility_rate": noisy_feasible,
        "noisy_optimal_probability": noisy_optimal,
        "shots": shots,
        "seed": seed,
        "one_qubit_error": one_qubit_error,
        "two_qubit_error": two_qubit_error,
        "promotion_decision": "NOT_PROMOTED_CLASSICAL_EXACT_BASELINE_DOMINATES_TOY_INSTANCE",
        "claim_control": "This is a frozen synthetic surrogate used to validate the QRF application pipeline. It is not a calibrated EM model, mission logistics model, real-QPU result, or quantum-advantage demonstration.",
    }
    digest_payload = dict(payload)
    digest_payload["exact_optimal_bitstrings"] = list(payload["exact_optimal_bitstrings"])
    digest = sha256(json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return QAOABenchmarkResult(result_digest=f"sha256:{digest}", **payload)


def metasurface_surrogate_problem() -> BinaryQuadraticProblem:
    # Four binary tile phase states on a ring. Penalize equal neighboring states.
    # Equality penalty per edge: 1 - xi - xj + 2 xi*xj.
    return BinaryQuadraticProblem(
        problem_id="WS-META-QO-001-SYNTH-RING4",
        project="WS-METASURFACE",
        description="Synthetic four-tile alternating-state surrogate; not calibrated EM physics.",
        linear=(-2.0, -2.0, -2.0, -2.0),
        quadratic={(0, 1): 2.0, (1, 2): 2.0, (2, 3): 2.0, (0, 3): 2.0},
        constant=4.0,
        feasibility_rule="always",
    )


def logistics_surrogate_problem() -> BinaryQuadraticProblem:
    # Select exactly one of four route/assignment candidates with declared costs.
    # QUBO = cost*x + P(sum(x)-1)^2, P=6.
    penalty = 6.0
    costs = (3.0, 1.0, 4.0, 2.0)
    return BinaryQuadraticProblem(
        problem_id="WS-LOG-QO-001-SYNTH-CHOICE4",
        project="WS-AUTONOMOUS-LOGISTICS",
        description="Synthetic one-of-four route assignment surrogate; not an operational mission plan.",
        linear=tuple(cost - penalty for cost in costs),
        quadratic={(i, j): 2.0 * penalty for i in range(4) for j in range(i + 1, 4)},
        constant=penalty,
        feasibility_rule="exactly_one",
    )

from __future__ import annotations

import math
from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


class BasisKind(str, Enum):
    PRIME = "PRIME"
    CONTIGUOUS = "CONTIGUOUS"
    COMPOSITE = "COMPOSITE"


class AblationOutcome(str, Enum):
    PRIME_ADVANTAGE_OBSERVED_IN_THIS_BENCHMARK = (
        "PRIME_ADVANTAGE_OBSERVED_IN_THIS_BENCHMARK"
    )
    NO_GENERAL_PRIME_ADVANTAGE_OBSERVED = "NO_GENERAL_PRIME_ADVANTAGE_OBSERVED"
    INCONCLUSIVE = "INCONCLUSIVE"


class SignalComponent(BaseModel):
    frequency_index: int = Field(ge=1)
    amplitude: float = Field(gt=0.0)
    phase_radians: float = 0.0


class ScenarioDefinition(BaseModel):
    scenario_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    components: tuple[SignalComponent, ...]

    @model_validator(mode="after")
    def requires_components(self) -> "ScenarioDefinition":
        if not self.components:
            raise ValueError("scenario requires at least one component")
        return self


class BasisResult(BaseModel):
    basis: BasisKind
    selected_indices: tuple[int, ...]
    rank: int = Field(ge=1)
    basis_terms: int = Field(ge=2)
    projection_sample_operations: int = Field(ge=1)
    relative_l2_error: float = Field(ge=0.0)
    energy_retained_fraction: float = Field(ge=0.0, le=1.0)
    max_normalized_cross_correlation: float = Field(ge=0.0)
    gram_diagonal_ratio: float = Field(ge=1.0)


class ScenarioResult(BaseModel):
    scenario_id: str
    purpose: str
    results: tuple[BasisResult, ...]
    winner: BasisKind | None


class AblationSummary(BaseModel):
    mean_relative_l2_error: dict[BasisKind, float]
    wins: dict[BasisKind, int]
    prime_dominates_every_scenario: bool
    outcome: AblationOutcome


class PrimeBasisAblationReport(BaseModel):
    qualification_id: str = "WS-QE-2026-PRI-001"
    benchmark_version: str = "1.0"
    sample_count: int = Field(ge=16)
    rank: int = Field(ge=1)
    scenarios: tuple[ScenarioResult, ...]
    summary: AblationSummary
    capability_status: CapabilityStatus = CapabilityStatus.SIMULATED_ONLY
    physical_validation_performed: bool = False
    quantum_physics_claimed: bool = False
    preferred_basis_for_general_use: BasisKind | None = None
    claims_boundary: tuple[str, ...] = (
        "This is a deterministic synthetic numerical ablation, not physical validation.",
        "Prime indexing is evaluated as a numerical selection rule, not a quantum law.",
        "A favorable case does not establish general superiority; adversarial and null cases are retained.",
    )
    report_digest: str | None = None


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    limit = int(math.isqrt(value))
    for divisor in range(3, limit + 1, 2):
        if value % divisor == 0:
            return False
    return True


def _indices_for_basis(kind: BasisKind, *, rank: int, max_index: int) -> tuple[int, ...]:
    if rank < 1:
        raise ValueError("rank must be >= 1")
    if max_index < 1:
        raise ValueError("max_index must be >= 1")

    if kind == BasisKind.CONTIGUOUS:
        values = tuple(range(1, min(max_index, rank) + 1))
    elif kind == BasisKind.PRIME:
        values = tuple(value for value in range(2, max_index + 1) if is_prime(value))[:rank]
    elif kind == BasisKind.COMPOSITE:
        values = tuple(
            value
            for value in range(4, max_index + 1)
            if value > 1 and not is_prime(value)
        )[:rank]
    else:  # pragma: no cover - Enum protects callers
        raise ValueError(f"unsupported basis: {kind}")

    if len(values) != rank:
        raise ValueError(f"{kind.value} basis cannot supply rank {rank} below index {max_index}")
    return values


def _signal(sample_count: int, components: Iterable[SignalComponent]) -> tuple[float, ...]:
    values: list[float] = []
    for sample in range(sample_count):
        angle_scale = (2.0 * math.pi * sample) / sample_count
        value = 0.0
        for component in components:
            value += component.amplitude * math.cos(
                (component.frequency_index * angle_scale) + component.phase_radians
            )
        values.append(value)
    return tuple(values)


def _basis_vectors(sample_count: int, indices: tuple[int, ...]) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for frequency in indices:
        cosine = tuple(
            math.cos((2.0 * math.pi * frequency * sample) / sample_count)
            for sample in range(sample_count)
        )
        sine = tuple(
            math.sin((2.0 * math.pi * frequency * sample) / sample_count)
            for sample in range(sample_count)
        )
        vectors.extend((cosine, sine))
    return tuple(vectors)


def _dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _orthogonality_metrics(vectors: tuple[tuple[float, ...], ...]) -> tuple[float, float]:
    diagonals = [_dot(vector, vector) for vector in vectors]
    min_diagonal = min(diagonals)
    max_diagonal = max(diagonals)
    if min_diagonal <= 0:
        raise ValueError("degenerate basis vector")

    max_cross = 0.0
    for left_index, left in enumerate(vectors):
        for right_index in range(left_index + 1, len(vectors)):
            right = vectors[right_index]
            denominator = math.sqrt(diagonals[left_index] * diagonals[right_index])
            max_cross = max(max_cross, abs(_dot(left, right)) / denominator)
    return max_cross, max_diagonal / min_diagonal


def _project_and_score(
    signal: tuple[float, ...],
    *,
    kind: BasisKind,
    indices: tuple[int, ...],
) -> BasisResult:
    sample_count = len(signal)
    reconstruction = [0.0] * sample_count
    for frequency in indices:
        cosine_coefficient = (2.0 / sample_count) * sum(
            value * math.cos((2.0 * math.pi * frequency * sample) / sample_count)
            for sample, value in enumerate(signal)
        )
        sine_coefficient = (2.0 / sample_count) * sum(
            value * math.sin((2.0 * math.pi * frequency * sample) / sample_count)
            for sample, value in enumerate(signal)
        )
        for sample in range(sample_count):
            angle = (2.0 * math.pi * frequency * sample) / sample_count
            reconstruction[sample] += (
                cosine_coefficient * math.cos(angle)
                + sine_coefficient * math.sin(angle)
            )

    residual_energy = sum(
        (observed - predicted) ** 2
        for observed, predicted in zip(signal, reconstruction, strict=True)
    )
    total_energy = sum(value * value for value in signal)
    if total_energy <= 0:
        raise ValueError("signal energy must be positive")

    relative_l2_error = math.sqrt(residual_energy / total_energy)
    energy_retained = max(0.0, min(1.0, 1.0 - (residual_energy / total_energy)))
    vectors = _basis_vectors(sample_count, indices)
    cross, diagonal_ratio = _orthogonality_metrics(vectors)

    return BasisResult(
        basis=kind,
        selected_indices=indices,
        rank=len(indices),
        basis_terms=len(indices) * 2,
        projection_sample_operations=sample_count * len(indices) * 2,
        relative_l2_error=relative_l2_error,
        energy_retained_fraction=energy_retained,
        max_normalized_cross_correlation=cross,
        gram_diagonal_ratio=diagonal_ratio,
    )


def default_scenarios() -> tuple[ScenarioDefinition, ...]:
    def components(*items: tuple[int, float, float]) -> tuple[SignalComponent, ...]:
        return tuple(
            SignalComponent(frequency_index=freq, amplitude=amp, phase_radians=phase)
            for freq, amp, phase in items
        )

    return (
        ScenarioDefinition(
            scenario_id="smooth_low_frequency",
            purpose="control case favoring low-order contiguous modes",
            components=components(
                (1, 1.0, 0.10),
                (2, 0.70, 0.20),
                (3, 0.45, -0.30),
                (4, 0.30, 0.40),
                (5, 0.20, -0.15),
            ),
        ),
        ScenarioDefinition(
            scenario_id="prime_sparse",
            purpose="positive-control case intentionally concentrated on prime indices",
            components=components(
                (2, 1.0, 0.00),
                (3, 0.80, 0.25),
                (5, 0.65, -0.40),
                (7, 0.50, 0.15),
                (11, 0.35, -0.20),
            ),
        ),
        ScenarioDefinition(
            scenario_id="composite_sparse",
            purpose="negative-control case intentionally concentrated on composite indices",
            components=components(
                (4, 1.0, 0.05),
                (6, 0.80, -0.20),
                (8, 0.65, 0.35),
                (9, 0.50, -0.10),
                (10, 0.35, 0.30),
            ),
        ),
        ScenarioDefinition(
            scenario_id="mixed_structure",
            purpose="mixed case with prime, composite, and low-order content",
            components=components(
                (1, 0.90, 0.00),
                (2, 0.75, 0.20),
                (4, 0.60, -0.25),
                (5, 0.50, 0.35),
                (7, 0.40, -0.10),
                (9, 0.30, 0.45),
            ),
        ),
        ScenarioDefinition(
            scenario_id="broadband_decay",
            purpose="broadband control with amplitude decreasing by frequency index",
            components=tuple(
                SignalComponent(
                    frequency_index=frequency,
                    amplitude=1.0 / frequency,
                    phase_radians=((frequency % 5) - 2) * 0.11,
                )
                for frequency in range(1, 16)
            ),
        ),
    )


def run_prime_basis_ablation(
    *,
    sample_count: int = 64,
    rank: int = 5,
    scenarios: tuple[ScenarioDefinition, ...] | None = None,
    winner_tolerance: float = 1e-12,
) -> PrimeBasisAblationReport:
    """Compare equal-rank Fourier mode-selection rules on deterministic synthetic signals.

    This is a numerical ablation only. Selecting prime-numbered Fourier modes is an
    operational proxy for testing a prime-indexed representation. It neither tests
    the complete multi-physics formulation nor establishes a quantum mechanism.
    """
    if sample_count < 16 or sample_count % 2:
        raise ValueError("sample_count must be an even integer >= 16")
    if rank < 1:
        raise ValueError("rank must be >= 1")
    if winner_tolerance < 0:
        raise ValueError("winner_tolerance must be >= 0")

    active_scenarios = scenarios or default_scenarios()
    if not active_scenarios:
        raise ValueError("at least one scenario is required")

    max_index = (sample_count // 2) - 1
    selections = {
        kind: _indices_for_basis(kind, rank=rank, max_index=max_index)
        for kind in BasisKind
    }

    scenario_results: list[ScenarioResult] = []
    error_accumulator = {kind: [] for kind in BasisKind}
    wins = {kind: 0 for kind in BasisKind}

    for scenario in active_scenarios:
        if max(component.frequency_index for component in scenario.components) > max_index:
            raise ValueError(
                f"scenario {scenario.scenario_id} contains frequency above usable limit {max_index}"
            )
        signal = _signal(sample_count, scenario.components)
        results = tuple(
            _project_and_score(signal, kind=kind, indices=selections[kind])
            for kind in BasisKind
        )
        for result in results:
            error_accumulator[result.basis].append(result.relative_l2_error)

        minimum_error = min(result.relative_l2_error for result in results)
        tied = [
            result.basis
            for result in results
            if abs(result.relative_l2_error - minimum_error) <= winner_tolerance
        ]
        winner = tied[0] if len(tied) == 1 else None
        if winner is not None:
            wins[winner] += 1

        scenario_results.append(
            ScenarioResult(
                scenario_id=scenario.scenario_id,
                purpose=scenario.purpose,
                results=results,
                winner=winner,
            )
        )

    prime_dominates = True
    prime_strictly_better_somewhere = False
    for scenario in scenario_results:
        by_basis = {result.basis: result.relative_l2_error for result in scenario.results}
        prime_error = by_basis[BasisKind.PRIME]
        for baseline in (BasisKind.CONTIGUOUS, BasisKind.COMPOSITE):
            baseline_error = by_basis[baseline]
            if prime_error > baseline_error + winner_tolerance:
                prime_dominates = False
            if prime_error + winner_tolerance < baseline_error:
                prime_strictly_better_somewhere = True

    prime_dominates = prime_dominates and prime_strictly_better_somewhere
    mean_errors = {
        kind: sum(values) / len(values)
        for kind, values in error_accumulator.items()
    }

    if prime_dominates:
        outcome = AblationOutcome.PRIME_ADVANTAGE_OBSERVED_IN_THIS_BENCHMARK
        preferred_basis = BasisKind.PRIME
    else:
        any_material_prime_loss = any(
            result.winner not in {None, BasisKind.PRIME}
            for result in scenario_results
        )
        outcome = (
            AblationOutcome.NO_GENERAL_PRIME_ADVANTAGE_OBSERVED
            if any_material_prime_loss
            else AblationOutcome.INCONCLUSIVE
        )
        preferred_basis = None

    report = PrimeBasisAblationReport(
        sample_count=sample_count,
        rank=rank,
        scenarios=tuple(scenario_results),
        summary=AblationSummary(
            mean_relative_l2_error=mean_errors,
            wins=wins,
            prime_dominates_every_scenario=prime_dominates,
            outcome=outcome,
        ),
        preferred_basis_for_general_use=preferred_basis,
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_prime_basis_ablation_report(report: PrimeBasisAblationReport) -> bool:
    expected = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.report_digest == expected

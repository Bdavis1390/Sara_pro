"""WS-QBENCH-MGRAPH v0.6 topology × energy-scale interaction ablation.

This module tests a narrower hypothesis suggested by v0.3-v0.4:
magnetic-graph connectivity can remain scale-free while physical localization
depends on the hopping/onsite energy ratio.  It therefore evaluates a paired
*difference-in-differences* interaction contrast instead of treating lambda1
as a universal localization predictor.

No source-paper parameter is inferred here.  All Hamiltonian scale ratios are
explicit inputs and exact Figure 4 reproduction remains source-lock blocked.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np

from .localization_ablation_v04 import (
    inverse_participation_ratios,
    phase_stripped_hopping,
    physical_hamiltonian_from_hopping,
    randomized_phase_hopping,
)
from .magnetic_graph import floquet_rabi_hopping
from .phase_null_v03 import permute_delta_sign_topology


@dataclass(frozen=True)
class FactorialInteractionSummary:
    variant: str
    eta: float
    nmax: int
    omega0: float
    h_parallel_over_omega0: float
    h0_over_omega0: float
    reference_ratio: float
    target_ratio: float
    eigenstates: int
    repetitions: int
    source_ref_mean_ipr: float
    source_target_mean_ipr: float
    null_ref_mean_ipr: float
    null_target_mean_ipr: float
    topology_effect_ref: float
    topology_effect_target: float
    interaction_mean: float
    interaction_std: float
    interaction_min: float
    interaction_max: float
    positive_fraction: float

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def difference_in_differences(
    source_ref: float,
    source_target: float,
    null_ref: float,
    null_target: float,
) -> float:
    """Return the topology × scale interaction contrast.

    Positive values mean the source topology's IPR advantage relative to the
    null becomes more positive at ``target`` than at ``reference``.  Zero is
    the additive/no-interaction expectation.
    """
    return (float(source_target) - float(null_target)) - (
        float(source_ref) - float(null_ref)
    )


def _mean_ipr(
    hopping: np.ndarray,
    *,
    omega0: float,
    h_perp_over_omega0: float,
    h_parallel_over_omega0: float,
    h0_over_omega0: float,
    eigenstates: int,
) -> float:
    if omega0 <= 0.0:
        raise ValueError("omega0 must be positive")
    if h_perp_over_omega0 < 0.0:
        raise ValueError("h_perp_over_omega0 must be non-negative")
    if eigenstates <= 0:
        raise ValueError("eigenstates must be positive")

    h = physical_hamiltonian_from_hopping(
        hopping,
        omega0=omega0,
        h_perp=float(h_perp_over_omega0) * omega0,
        h_parallel=float(h_parallel_over_omega0) * omega0,
        h0=float(h0_over_omega0) * omega0,
    )
    _energies, vectors = np.linalg.eigh(h)
    count = min(int(eigenstates), vectors.shape[1])
    return float(np.mean(inverse_participation_ratios(vectors[:, :count])))


def _summarize_variant(
    *,
    variant: str,
    source: np.ndarray,
    eta: float,
    nmax: int,
    omega0: float,
    h_parallel_over_omega0: float,
    h0_over_omega0: float,
    reference_ratio: float,
    target_ratio: float,
    eigenstates: int,
    repetitions: int,
    seed: int,
) -> FactorialInteractionSummary:
    source_ref = _mean_ipr(
        source,
        omega0=omega0,
        h_perp_over_omega0=reference_ratio,
        h_parallel_over_omega0=h_parallel_over_omega0,
        h0_over_omega0=h0_over_omega0,
        eigenstates=eigenstates,
    )
    source_target = _mean_ipr(
        source,
        omega0=omega0,
        h_perp_over_omega0=target_ratio,
        h_parallel_over_omega0=h_parallel_over_omega0,
        h0_over_omega0=h0_over_omega0,
        eigenstates=eigenstates,
    )

    rng = np.random.default_rng(seed)
    if variant == "phase_stripped":
        nulls = [phase_stripped_hopping(source)]
    else:
        if repetitions <= 0:
            raise ValueError("repetitions must be positive")
        nulls = []
        for _ in range(repetitions):
            if variant == "delta_sign_permuted":
                nulls.append(permute_delta_sign_topology(source, rng))
            elif variant == "randomized_phase":
                nulls.append(randomized_phase_hopping(source, rng))
            else:
                raise ValueError("unsupported variant")

    null_ref = np.empty(len(nulls), dtype=float)
    null_target = np.empty(len(nulls), dtype=float)
    interaction = np.empty(len(nulls), dtype=float)
    for index, null in enumerate(nulls):
        null_ref[index] = _mean_ipr(
            null,
            omega0=omega0,
            h_perp_over_omega0=reference_ratio,
            h_parallel_over_omega0=h_parallel_over_omega0,
            h0_over_omega0=h0_over_omega0,
            eigenstates=eigenstates,
        )
        null_target[index] = _mean_ipr(
            null,
            omega0=omega0,
            h_perp_over_omega0=target_ratio,
            h_parallel_over_omega0=h_parallel_over_omega0,
            h0_over_omega0=h0_over_omega0,
            eigenstates=eigenstates,
        )
        interaction[index] = difference_in_differences(
            source_ref,
            source_target,
            null_ref[index],
            null_target[index],
        )

    null_ref_mean = float(np.mean(null_ref))
    null_target_mean = float(np.mean(null_target))
    return FactorialInteractionSummary(
        variant=variant,
        eta=float(eta),
        nmax=int(nmax),
        omega0=float(omega0),
        h_parallel_over_omega0=float(h_parallel_over_omega0),
        h0_over_omega0=float(h0_over_omega0),
        reference_ratio=float(reference_ratio),
        target_ratio=float(target_ratio),
        eigenstates=min(int(eigenstates), 2 * (int(nmax) + 1)),
        repetitions=len(nulls),
        source_ref_mean_ipr=source_ref,
        source_target_mean_ipr=source_target,
        null_ref_mean_ipr=null_ref_mean,
        null_target_mean_ipr=null_target_mean,
        topology_effect_ref=source_ref - null_ref_mean,
        topology_effect_target=source_target - null_target_mean,
        interaction_mean=float(np.mean(interaction)),
        interaction_std=float(np.std(interaction, ddof=0)),
        interaction_min=float(np.min(interaction)),
        interaction_max=float(np.max(interaction)),
        positive_fraction=float(np.mean(interaction > 0.0)),
    )


def factorial_interaction_ablation(
    nmax: int,
    eta: float,
    *,
    reference_ratio: float,
    target_ratio: float,
    omega0: float = 1.0,
    h_parallel_over_omega0: float = 0.0,
    h0_over_omega0: float = 0.0,
    eigenstates: int = 30,
    repetitions: int = 20,
    seed: int = 9675,
) -> dict[str, dict[str, float | int | str]]:
    """Evaluate paired source-vs-null topology × scale interactions."""
    if reference_ratio < 0.0 or target_ratio < 0.0:
        raise ValueError("scale ratios must be non-negative")
    source = floquet_rabi_hopping(nmax=nmax, eta=eta, h_perp=1.0)
    output: dict[str, dict[str, float | int | str]] = {}
    for offset, variant in enumerate(
        ("phase_stripped", "delta_sign_permuted", "randomized_phase")
    ):
        summary = _summarize_variant(
            variant=variant,
            source=source,
            eta=eta,
            nmax=nmax,
            omega0=omega0,
            h_parallel_over_omega0=h_parallel_over_omega0,
            h0_over_omega0=h0_over_omega0,
            reference_ratio=reference_ratio,
            target_ratio=target_ratio,
            eigenstates=eigenstates,
            repetitions=repetitions,
            seed=seed + 10000 * offset,
        )
        output[variant] = summary.to_dict()
    return output


def interaction_sweep(
    etas: Iterable[float],
    ratios: Iterable[float],
    *,
    reference_ratio: float,
    nmax: int = 80,
    omega0: float = 1.0,
    h_parallel_over_omega0: float = 0.0,
    h0_over_omega0: float = 0.0,
    eigenstates: int = 30,
    repetitions: int = 20,
    seed: int = 9675,
) -> list[dict[str, object]]:
    """Sweep target scale ratios against one predeclared reference ratio."""
    rows: list[dict[str, object]] = []
    for eta_index, eta in enumerate(etas):
        for ratio_index, ratio in enumerate(ratios):
            ratio = float(ratio)
            rows.append(
                {
                    "eta": float(eta),
                    "reference_ratio": float(reference_ratio),
                    "target_ratio": ratio,
                    "result": factorial_interaction_ablation(
                        nmax=nmax,
                        eta=float(eta),
                        reference_ratio=float(reference_ratio),
                        target_ratio=ratio,
                        omega0=omega0,
                        h_parallel_over_omega0=h_parallel_over_omega0,
                        h0_over_omega0=h0_over_omega0,
                        eigenstates=eigenstates,
                        repetitions=repetitions,
                        seed=seed + 1000 * eta_index + 10 * ratio_index,
                    ),
                }
            )
    return rows

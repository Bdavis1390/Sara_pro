"""WS-QBENCH-MGRAPH v0.4 parameterized Hamiltonian/IPR ablation.

This module implements the finite Fock-space Hamiltonian corresponding to the
source paper's Eq. (3)/End Matter E1 while keeping all physical scale ratios
explicit. It does *not* claim to reproduce Figure 4e/f until the source
normalization is locked.

The purpose is adversarial: compare localization under the source hopping
phase topology against phase-controlled nulls without silently assuming a
Hamiltonian normalization.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np

from .magnetic_graph import floquet_rabi_hopping
from .phase_null_v03 import permute_delta_sign_topology


@dataclass(frozen=True)
class LocalizationSummary:
    variant: str
    eta: float
    nmax: int
    omega0: float
    h_perp: float
    h_parallel: float
    h0: float
    eigenstates: int
    mean_ipr: float
    median_ipr: float
    min_ipr: float
    max_ipr: float
    mean_participation_number: float
    mean_energy: float
    min_energy: float
    max_energy: float

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class EnsembleLocalizationSummary:
    variant: str
    eta: float
    nmax: int
    omega0: float
    h_perp: float
    h_parallel: float
    h0: float
    eigenstates: int
    repetitions: int
    mean_of_mean_ipr: float
    std_of_mean_ipr: float
    min_of_mean_ipr: float
    max_of_mean_ipr: float

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


def physical_hamiltonian_from_hopping(
    hopping: np.ndarray,
    *,
    omega0: float,
    h_perp: float,
    h_parallel: float = 0.0,
    h0: float = 0.0,
) -> np.ndarray:
    """Build finite H_C in units where hbar=1.

    Basis ordering is (+, n=0..Nmax) followed by (-, n=0..Nmax):

        H = [[B + h_parallel I, h_perp K],
             [h_perp K^dagger, B - h_parallel I]],

    with B_nn = n*omega0 + h0. ``hopping`` is the dimensionless displacement
    block <n|D(+2 i eta)|m>.
    """
    k = np.asarray(hopping, dtype=np.complex128)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("hopping must be square")
    if omega0 <= 0.0:
        raise ValueError("omega0 must be positive")
    if h_perp < 0.0:
        raise ValueError("h_perp must be non-negative")

    dim = k.shape[0]
    identity = np.eye(dim, dtype=np.complex128)
    b = np.diag(np.arange(dim, dtype=float) * float(omega0) + float(h0)).astype(
        np.complex128
    )
    upper_left = b + float(h_parallel) * identity
    lower_right = b - float(h_parallel) * identity
    upper_right = float(h_perp) * k
    hamiltonian = np.block(
        [[upper_left, upper_right], [upper_right.conj().T, lower_right]]
    )
    return 0.5 * (hamiltonian + hamiltonian.conj().T)


def inverse_participation_ratios(eigenvectors: np.ndarray) -> np.ndarray:
    """Return IPR=sum_v |psi_v|^4 for normalized eigenvector columns."""
    vectors = np.asarray(eigenvectors, dtype=np.complex128)
    if vectors.ndim != 2:
        raise ValueError("eigenvectors must be a two-dimensional matrix")
    norms = np.sum(np.abs(vectors) ** 2, axis=0)
    if np.any(norms <= 0.0):
        raise ValueError("zero-norm eigenvector encountered")
    normalized = vectors / np.sqrt(norms)[None, :]
    return np.sum(np.abs(normalized) ** 4, axis=0).real


def _summarize(
    *,
    variant: str,
    hopping: np.ndarray,
    eta: float,
    nmax: int,
    omega0: float,
    h_perp: float,
    h_parallel: float,
    h0: float,
    eigenstates: int,
) -> LocalizationSummary:
    hamiltonian = physical_hamiltonian_from_hopping(
        hopping,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
    )
    energies, vectors = np.linalg.eigh(hamiltonian)
    count = min(int(eigenstates), len(energies))
    if count <= 0:
        raise ValueError("eigenstates must be positive")
    energies = energies[:count]
    ipr = inverse_participation_ratios(vectors[:, :count])
    participation = 1.0 / ipr
    return LocalizationSummary(
        variant=variant,
        eta=float(eta),
        nmax=nmax,
        omega0=float(omega0),
        h_perp=float(h_perp),
        h_parallel=float(h_parallel),
        h0=float(h0),
        eigenstates=count,
        mean_ipr=float(np.mean(ipr)),
        median_ipr=float(np.median(ipr)),
        min_ipr=float(np.min(ipr)),
        max_ipr=float(np.max(ipr)),
        mean_participation_number=float(np.mean(participation)),
        mean_energy=float(np.mean(energies)),
        min_energy=float(np.min(energies)),
        max_energy=float(np.max(energies)),
    )


def phase_stripped_hopping(hopping: np.ndarray) -> np.ndarray:
    """Magnitude-only positive hopping null."""
    return np.abs(np.asarray(hopping, dtype=np.complex128)).astype(np.complex128)


def randomized_phase_hopping(
    hopping: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Preserve every magnitude while independently randomizing K-entry phases.

    The physical Hamiltonian remains Hermitian because the opposite block is
    constructed as K^dagger. The resulting K need not itself be symmetric; this
    is intentionally a nonphysical phase-randomization null.
    """
    k = np.asarray(hopping, dtype=np.complex128)
    phases = rng.uniform(-np.pi, np.pi, size=k.shape)
    return np.abs(k) * np.exp(1j * phases)


def source_localization(
    nmax: int,
    eta: float,
    *,
    omega0: float,
    h_perp: float,
    h_parallel: float = 0.0,
    h0: float = 0.0,
    eigenstates: int = 30,
) -> LocalizationSummary:
    """Summarize the source hopping topology at an explicit normalization."""
    hopping = floquet_rabi_hopping(nmax=nmax, eta=eta, h_perp=1.0)
    return _summarize(
        variant="source_topology",
        hopping=hopping,
        eta=eta,
        nmax=nmax,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
    )


def phase_stripped_localization(
    nmax: int,
    eta: float,
    *,
    omega0: float,
    h_perp: float,
    h_parallel: float = 0.0,
    h0: float = 0.0,
    eigenstates: int = 30,
) -> LocalizationSummary:
    hopping = floquet_rabi_hopping(nmax=nmax, eta=eta, h_perp=1.0)
    return _summarize(
        variant="phase_stripped",
        hopping=phase_stripped_hopping(hopping),
        eta=eta,
        nmax=nmax,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
    )


def _ensemble_localization(
    *,
    variant: str,
    nmax: int,
    eta: float,
    omega0: float,
    h_perp: float,
    h_parallel: float,
    h0: float,
    eigenstates: int,
    repetitions: int,
    seed: int,
) -> EnsembleLocalizationSummary:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    source = floquet_rabi_hopping(nmax=nmax, eta=eta, h_perp=1.0)
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions, dtype=float)
    for index in range(repetitions):
        if variant == "delta_sign_permuted":
            null = permute_delta_sign_topology(source, rng)
        elif variant == "randomized_phase":
            null = randomized_phase_hopping(source, rng)
        else:
            raise ValueError("unsupported ensemble variant")
        row = _summarize(
            variant=variant,
            hopping=null,
            eta=eta,
            nmax=nmax,
            omega0=omega0,
            h_perp=h_perp,
            h_parallel=h_parallel,
            h0=h0,
            eigenstates=eigenstates,
        )
        means[index] = row.mean_ipr

    return EnsembleLocalizationSummary(
        variant=variant,
        eta=float(eta),
        nmax=nmax,
        omega0=float(omega0),
        h_perp=float(h_perp),
        h_parallel=float(h_parallel),
        h0=float(h0),
        eigenstates=min(eigenstates, 2 * (nmax + 1)),
        repetitions=repetitions,
        mean_of_mean_ipr=float(np.mean(means)),
        std_of_mean_ipr=float(np.std(means, ddof=0)),
        min_of_mean_ipr=float(np.min(means)),
        max_of_mean_ipr=float(np.max(means)),
    )


def localization_ablation(
    nmax: int,
    eta: float,
    *,
    omega0: float,
    h_perp: float,
    h_parallel: float = 0.0,
    h0: float = 0.0,
    eigenstates: int = 30,
    repetitions: int = 20,
    seed: int = 9675,
) -> dict[str, dict[str, float | int | str]]:
    """Run source, stripped, Delta-sign and fully randomized phase controls."""
    source = source_localization(
        nmax,
        eta,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
    )
    stripped = phase_stripped_localization(
        nmax,
        eta,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
    )
    delta_null = _ensemble_localization(
        variant="delta_sign_permuted",
        nmax=nmax,
        eta=eta,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
        repetitions=repetitions,
        seed=seed,
    )
    random_null = _ensemble_localization(
        variant="randomized_phase",
        nmax=nmax,
        eta=eta,
        omega0=omega0,
        h_perp=h_perp,
        h_parallel=h_parallel,
        h0=h0,
        eigenstates=eigenstates,
        repetitions=repetitions,
        seed=seed + 1,
    )
    return {
        "source_topology": source.to_dict(),
        "phase_stripped": stripped.to_dict(),
        "delta_sign_permuted": delta_null.to_dict(),
        "randomized_phase": random_null.to_dict(),
    }


def sweep_scale_ratio(
    etas: Iterable[float],
    h_perp_over_omega0: Iterable[float],
    *,
    nmax: int = 80,
    omega0: float = 1.0,
    h_parallel_over_omega0: float = 0.0,
    h0_over_omega0: float = 0.0,
    eigenstates: int = 30,
    repetitions: int = 20,
    seed: int = 9675,
) -> list[dict[str, object]]:
    """Sensitivity sweep that avoids assuming the unpublished Figure-4 scale ratio."""
    if omega0 <= 0.0:
        raise ValueError("omega0 must be positive")
    rows: list[dict[str, object]] = []
    for eta_index, eta in enumerate(etas):
        for ratio_index, ratio in enumerate(h_perp_over_omega0):
            ratio = float(ratio)
            if ratio < 0.0:
                raise ValueError("h_perp_over_omega0 values must be non-negative")
            rows.append(
                {
                    "eta": float(eta),
                    "h_perp_over_omega0": ratio,
                    "h_parallel_over_omega0": float(h_parallel_over_omega0),
                    "result": localization_ablation(
                        nmax=nmax,
                        eta=float(eta),
                        omega0=omega0,
                        h_perp=ratio * omega0,
                        h_parallel=float(h_parallel_over_omega0) * omega0,
                        h0=float(h0_over_omega0) * omega0,
                        eigenstates=eigenstates,
                        repetitions=repetitions,
                        seed=seed + 1000 * eta_index + 10 * ratio_index,
                    ),
                }
            )
    return rows

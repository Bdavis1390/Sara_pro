"""WS-QBENCH-MGRAPH v0.8 author-aligned Figure 4e/f candidate reproduction.

The Hamiltonian normalization follows the corresponding-author clarification:
hbar = omega0 = 1, h0 = 0, |h_parallel| = 0, and the transverse/perpendicular
coefficient is mapped to h_perp = 1/2.  Exact source-figure reproduction remains
blocked until Code S1 is locally acquired and the notation mapping is verified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .localization_ablation_v04 import (
    inverse_participation_ratios,
    physical_hamiltonian_from_hopping,
)
from .magnetic_graph import floquet_rabi_hopping


@dataclass(frozen=True)
class StateResolvedFigure4EF:
    eta: float
    nmax: int
    eigenstates: int
    energies: tuple[float, ...]
    ipr: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def state_resolved_figure4ef(
    eta: float,
    *,
    nmax: int = 200,
    eigenstates: int = 30,
) -> StateResolvedFigure4EF:
    """Return the first source-aligned eigenenergies and IPR values.

    This is a candidate reproduction under the Worldshepherd h_perp notation
    mapping. It is not an exact Figure 4e/f claim until Code S1 is verified.
    """
    if nmax < 1:
        raise ValueError("nmax must be positive")
    if eta < 0.0:
        raise ValueError("eta must be non-negative")
    if eigenstates <= 0:
        raise ValueError("eigenstates must be positive")

    hopping = floquet_rabi_hopping(nmax=nmax, eta=float(eta), h_perp=1.0)
    hamiltonian = physical_hamiltonian_from_hopping(
        hopping,
        omega0=1.0,
        h_perp=0.5,
        h_parallel=0.0,
        h0=0.0,
    )
    energies, vectors = np.linalg.eigh(hamiltonian)
    count = min(int(eigenstates), len(energies))
    energies = energies[:count]
    ipr = inverse_participation_ratios(vectors[:, :count])

    return StateResolvedFigure4EF(
        eta=float(eta),
        nmax=int(nmax),
        eigenstates=count,
        energies=tuple(float(x) for x in energies),
        ipr=tuple(float(x) for x in ipr),
    )


def adjacent_gap_diagnostic(
    eta: float,
    *,
    nmax: int = 200,
    eigenstates: int = 30,
) -> dict[str, float | int]:
    """Describe adjacent-energy compression without promoting a phase boundary."""
    row = state_resolved_figure4ef(
        eta,
        nmax=nmax,
        eigenstates=eigenstates,
    )
    energies = np.asarray(row.energies, dtype=float)
    if len(energies) < 2:
        raise ValueError("at least two eigenstates are required")
    gaps = np.diff(energies)
    return {
        "eta": float(eta),
        "nmax": int(nmax),
        "eigenstates": int(row.eigenstates),
        "min_adjacent_gap": float(np.min(gaps)),
        "median_adjacent_gap": float(np.median(gaps)),
        "count_gap_lt_1e-3": int(np.sum(gaps < 1e-3)),
        "count_gap_lt_1e-2": int(np.sum(gaps < 1e-2)),
    }

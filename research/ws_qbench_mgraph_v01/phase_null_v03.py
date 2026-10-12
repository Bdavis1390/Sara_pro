"""WS-QBENCH-MGRAPH v0.3 phase-topology adversarial controls.

The source magnetic graph has edge phases restricted by hopping-order parity and
the signs of associated Laguerre factors. This module asks a sharper question:
is the observed lambda1 explained only by edge magnitudes and coarse phase
classes, or does the *arrangement* of the sign topology matter?

The delta-sign permutation null preserves, for every hopping order Delta:
- every edge magnitude at its original matrix location;
- the phase-parity base i**Delta;
- symmetry of the hopping block;
- the exact multiset of positive/negative Laguerre signs within that Delta.

It randomizes only where those signs occur along a fixed hopping order. The null
is deliberately nonphysical and is used only as a falsification control.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .magnetic_graph import floquet_rabi_hopping


@dataclass(frozen=True)
class PhaseNullSummary:
    eta: float
    nmax: int
    repetitions: int
    seed: int
    original_lambda1: float
    null_mean: float
    null_std: float
    null_min: float
    null_max: float
    excess_over_null_mean: float
    z_score: float | None
    original_above_null_max: bool

    def to_dict(self) -> dict[str, float | int | bool | None]:
        return asdict(self)


def lambda1_from_hopping(hopping: np.ndarray) -> float:
    """Compute the smallest normalized magnetic-Laplacian eigenvalue from K."""
    k = np.asarray(hopping, dtype=np.complex128)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("hopping must be square")
    zero = np.zeros_like(k)
    adjacency = np.block([[zero, k], [k.conj().T, zero]])
    degree = np.sum(np.abs(adjacency), axis=1)
    if np.any(degree <= 0.0):
        raise ValueError("zero-degree node encountered")
    inv_sqrt = 1.0 / np.sqrt(degree)
    normalized = (inv_sqrt[:, None] * adjacency) * inv_sqrt[None, :]
    laplacian = np.eye(adjacency.shape[0], dtype=np.complex128) - normalized
    laplacian = 0.5 * (laplacian + laplacian.conj().T)
    return float(np.linalg.eigvalsh(laplacian)[0])


def _phase_base(delta: int) -> complex:
    return (1j) ** delta


def delta_signs(hopping: np.ndarray, delta: int, atol: float = 1e-14) -> list[int]:
    """Return the +/- Laguerre-sign sequence on one upper-triangle Delta band."""
    k = np.asarray(hopping, dtype=np.complex128)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("hopping must be square")
    dim = k.shape[0]
    if delta < 0 or delta >= dim:
        raise ValueError("delta out of range")
    base = _phase_base(delta)
    signs: list[int] = []
    for i in range(dim - delta):
        j = i + delta
        magnitude = abs(k[i, j])
        if magnitude <= atol:
            continue
        reduced = k[i, j] / (base * magnitude)
        if abs(reduced.imag) > 1e-10 or abs(abs(reduced.real) - 1.0) > 1e-9:
            raise ValueError("hopping phase is not compatible with the expected parity class")
        signs.append(1 if reduced.real >= 0.0 else -1)
    return signs


def permute_delta_sign_topology(
    hopping: np.ndarray,
    rng: np.random.Generator,
    atol: float = 1e-14,
) -> np.ndarray:
    """Shuffle Laguerre signs within each hopping-order band while preserving controls."""
    k = np.asarray(hopping, dtype=np.complex128)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("hopping must be square")
    if np.max(np.abs(k - k.T)) > 1e-10:
        raise ValueError("expected the source hopping block to be symmetric")

    dim = k.shape[0]
    magnitude = np.abs(k)
    out = np.zeros_like(k)

    for delta in range(dim):
        base = _phase_base(delta)
        positions: list[tuple[int, int]] = []
        signs: list[int] = []
        for i in range(dim - delta):
            j = i + delta
            if magnitude[i, j] <= atol:
                continue
            reduced = k[i, j] / (base * magnitude[i, j])
            if abs(reduced.imag) > 1e-10 or abs(abs(reduced.real) - 1.0) > 1e-9:
                raise ValueError("source phase is not a parity-compatible +/- sign")
            positions.append((i, j))
            signs.append(1 if reduced.real >= 0.0 else -1)

        shuffled = np.asarray(signs, dtype=int)
        rng.shuffle(shuffled)
        for (i, j), sign in zip(positions, shuffled):
            value = magnitude[i, j] * base * int(sign)
            out[i, j] = value
            out[j, i] = value

    return out


def phase_topology_null_ensemble(
    nmax: int,
    eta: float,
    repetitions: int = 100,
    seed: int = 9675,
) -> PhaseNullSummary:
    """Compare source lambda1 with Delta-sign-permuted topology nulls."""
    if nmax < 1:
        raise ValueError("nmax must be >= 1")
    if eta < 0.0:
        raise ValueError("eta must be non-negative")
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")

    hopping = floquet_rabi_hopping(nmax=nmax, eta=float(eta))
    original = lambda1_from_hopping(hopping)
    rng = np.random.default_rng(seed)
    null_values = np.empty(repetitions, dtype=float)
    for index in range(repetitions):
        null_hopping = permute_delta_sign_topology(hopping, rng)
        null_values[index] = lambda1_from_hopping(null_hopping)

    mean = float(np.mean(null_values))
    std = float(np.std(null_values, ddof=0))
    z_score = (original - mean) / std if std > 0.0 else None
    maximum = float(np.max(null_values))
    return PhaseNullSummary(
        eta=float(eta),
        nmax=nmax,
        repetitions=repetitions,
        seed=seed,
        original_lambda1=original,
        null_mean=mean,
        null_std=std,
        null_min=float(np.min(null_values)),
        null_max=maximum,
        excess_over_null_mean=original - mean,
        z_score=z_score,
        original_above_null_max=original > maximum,
    )

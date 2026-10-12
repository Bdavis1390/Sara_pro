"""Worldshepherd WS-QBENCH-MGRAPH v0.1.

A bounded numerical implementation of the Floquet-Rabi magnetic-graph
construction described by Yu, Piao & Park (Science Advances, 2026).

This module intentionally distinguishes paper-faithful quantities
(normalized magnetic Laplacian and its lowest eigenvalue) from
Worldshepherd diagnostic proxies (thresholded random-loop statistics).

Claim ceiling:
- IMPLEMENTED IN SOFTWARE
- SIMULATED ONLY
- SUPPORTED BY LITERATURE
- REQUIRES INDEPENDENT NUMERICAL REPRODUCTION
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import math
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class LoopStats:
    q: int
    requested_samples: int
    formed_loops: int
    formation_fraction: float
    frustrated_fraction: float
    trivial_fraction: float
    mean_geometric_strength: float
    edge_threshold: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class SweepPoint:
    eta: float
    lambda1: float
    lambda_max: float
    laplacian_hermiticity_error: float
    gauge_spectrum_error: float
    q2_frustrated_fraction: float
    q3_frustrated_fraction: float
    q4_frustrated_fraction: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def generalized_laguerre(n: int, alpha: int, x: float) -> float:
    """Evaluate L_n^(alpha)(x) using the three-term recurrence."""
    if n < 0 or alpha < 0:
        raise ValueError("n and alpha must be non-negative")
    if n == 0:
        return 1.0
    if n == 1:
        return 1.0 + alpha - x

    l_nm1 = 1.0
    l_n = 1.0 + alpha - x
    for k in range(1, n):
        l_np1 = ((2 * k + 1 + alpha - x) * l_n - (k + alpha) * l_nm1) / (k + 1)
        l_nm1, l_n = l_n, l_np1
    return float(l_n)


def displacement_matrix(nmax: int, eta: float, sign: int = +1) -> np.ndarray:
    """Return <n|D(sign*2 i eta)|m> for 0 <= n,m <= nmax.

    The finite Fock cutoff means the returned matrix is not exactly unitary at
    nonzero eta; that truncation error is expected and must not be misread as a
    physics result.
    """
    if nmax < 0:
        raise ValueError("nmax must be non-negative")
    if eta < 0:
        raise ValueError("eta must be non-negative")
    if sign not in (-1, +1):
        raise ValueError("sign must be +1 or -1")

    dim = nmax + 1
    out = np.zeros((dim, dim), dtype=np.complex128)
    x = 4.0 * eta * eta
    prefactor = math.exp(-2.0 * eta * eta)

    for n in range(dim):
        for m in range(dim):
            s = min(n, m)
            delta = abs(n - m)
            factorial_ratio = math.exp(
                0.5 * (math.lgamma(s + 1.0) - math.lgamma(s + delta + 1.0))
            )
            laguerre = generalized_laguerre(s, delta, x)
            phase_power = (sign * 2j * eta) ** delta
            out[n, m] = prefactor * phase_power * factorial_ratio * laguerre
    return out


def floquet_rabi_hopping(nmax: int, eta: float, h_perp: float = 1.0) -> np.ndarray:
    """Return the + -> - hopping block K for the static FR graph."""
    if h_perp <= 0:
        raise ValueError("h_perp must be positive")
    return float(h_perp) * displacement_matrix(nmax=nmax, eta=eta, sign=+1)


def floquet_rabi_adjacency(nmax: int, eta: float, h_perp: float = 1.0) -> np.ndarray:
    """Build the finite Hermitian bipartite FR magnetic adjacency matrix."""
    k = floquet_rabi_hopping(nmax=nmax, eta=eta, h_perp=h_perp)
    z = np.zeros_like(k)
    return np.block([[z, k], [k.conj().T, z]])


def normalized_magnetic_laplacian(adjacency: np.ndarray, atol: float = 1e-15) -> np.ndarray:
    """Return L = I - D^(-1/2) A D^(-1/2), D_ii=sum_j |A_ij|."""
    a = np.asarray(adjacency, dtype=np.complex128)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("adjacency must be square")
    hermiticity_error = float(np.max(np.abs(a - a.conj().T)))
    if hermiticity_error > 1e-10:
        raise ValueError(f"adjacency must be Hermitian; residual={hermiticity_error:g}")

    degree = np.sum(np.abs(a), axis=1)
    if np.any(degree <= atol):
        raise ValueError("isolated or numerically zero-degree node encountered")

    inv_sqrt = 1.0 / np.sqrt(degree)
    normalized = (inv_sqrt[:, None] * a) * inv_sqrt[None, :]
    lap = np.eye(a.shape[0], dtype=np.complex128) - normalized
    return 0.5 * (lap + lap.conj().T)


def magnetic_spectrum(nmax: int, eta: float, h_perp: float = 1.0) -> np.ndarray:
    """Sorted eigenvalues of the finite normalized magnetic Laplacian."""
    lap = normalized_magnetic_laplacian(
        floquet_rabi_adjacency(nmax=nmax, eta=eta, h_perp=h_perp)
    )
    return np.linalg.eigvalsh(lap)


def lambda1_metric(nmax: int, eta: float, h_perp: float = 1.0) -> float:
    """Lowest normalized-magnetic-Laplacian eigenvalue."""
    return float(magnetic_spectrum(nmax=nmax, eta=eta, h_perp=h_perp)[0])


def apply_local_gauge(adjacency: np.ndarray, phases: np.ndarray) -> np.ndarray:
    """Apply A -> U A U† for diagonal U=diag(exp(i*phase))."""
    a = np.asarray(adjacency, dtype=np.complex128)
    phases = np.asarray(phases, dtype=float)
    if phases.shape != (a.shape[0],):
        raise ValueError("phases length must equal adjacency dimension")
    u = np.exp(1j * phases)
    return (u[:, None] * a) * u.conj()[None, :]


def gauge_spectrum_residual(
    nmax: int,
    eta: float,
    h_perp: float = 1.0,
    seed: int = 0,
) -> float:
    """Maximum magnetic-Laplacian spectral change under a local gauge."""
    a = floquet_rabi_adjacency(nmax=nmax, eta=eta, h_perp=h_perp)
    original = np.linalg.eigvalsh(normalized_magnetic_laplacian(a))
    rng = np.random.default_rng(seed)
    gauged = apply_local_gauge(a, rng.uniform(-np.pi, np.pi, size=a.shape[0]))
    transformed = np.linalg.eigvalsh(normalized_magnetic_laplacian(gauged))
    return float(np.max(np.abs(original - transformed)))


def _loop_product(k: np.ndarray, plus_nodes: np.ndarray, minus_nodes: np.ndarray) -> complex:
    """Gauge-invariant alternating loop product over a bipartite hopping block."""
    q = len(plus_nodes)
    product = 1.0 + 0.0j
    for r in range(q):
        p_here = int(plus_nodes[r])
        p_next = int(plus_nodes[(r + 1) % q])
        m_here = int(minus_nodes[r])
        product *= k[p_here, m_here] * np.conj(k[p_next, m_here])
    return product


def sample_loop_statistics(
    nmax: int,
    eta: float,
    q: int,
    samples: int = 2000,
    rel_edge_threshold: float = 1e-3,
    seed: int = 0,
    phase_tolerance: float = 1e-8,
) -> LoopStats:
    """Sample thresholded closed-loop statistics as a WS diagnostic proxy.

    This is NOT claimed to reproduce the source paper's exact Monte Carlo
    procedure until its supplementary sampling conventions are independently
    matched. A sampled loop is formed only when every constituent edge exceeds
    rel_edge_threshold * max(|K|). A formed loop is classified as frustrated
    when cos(phi) < 0 outside the numerical tolerance band.
    """
    if q < 2:
        raise ValueError("q must be >= 2")
    if samples <= 0:
        raise ValueError("samples must be positive")
    dim = nmax + 1
    if q > dim:
        raise ValueError("q cannot exceed the Fock-space dimension")
    if not (0.0 <= rel_edge_threshold < 1.0):
        raise ValueError("rel_edge_threshold must be in [0,1)")

    k = floquet_rabi_hopping(nmax=nmax, eta=eta)
    threshold = float(rel_edge_threshold * np.max(np.abs(k)))
    rng = np.random.default_rng(seed)

    formed = 0
    frustrated = 0
    trivial = 0
    strengths: list[float] = []

    for _ in range(samples):
        plus_nodes = rng.choice(dim, size=q, replace=False)
        minus_nodes = rng.choice(dim, size=q, replace=False)

        edge_values: list[complex] = []
        for r in range(q):
            p_here = int(plus_nodes[r])
            p_next = int(plus_nodes[(r + 1) % q])
            m_here = int(minus_nodes[r])
            edge_values.extend((k[p_here, m_here], k[p_next, m_here]))

        if any(abs(edge) <= threshold for edge in edge_values):
            continue

        formed += 1
        product = _loop_product(k, plus_nodes, minus_nodes)
        if abs(product) == 0.0:
            continue
        strengths.append(float(abs(product) ** (1.0 / (2.0 * q))))
        c = math.cos(math.atan2(product.imag, product.real))
        if c < -phase_tolerance:
            frustrated += 1
        elif c > phase_tolerance:
            trivial += 1

    if formed:
        frustrated_fraction = frustrated / formed
        trivial_fraction = trivial / formed
        mean_strength = float(np.mean(strengths)) if strengths else 0.0
    else:
        frustrated_fraction = 0.0
        trivial_fraction = 0.0
        mean_strength = 0.0

    return LoopStats(
        q=q,
        requested_samples=samples,
        formed_loops=formed,
        formation_fraction=formed / samples,
        frustrated_fraction=frustrated_fraction,
        trivial_fraction=trivial_fraction,
        mean_geometric_strength=mean_strength,
        edge_threshold=threshold,
    )


def sweep_eta(
    etas: Iterable[float],
    nmax: int = 48,
    loop_samples: int = 1000,
    rel_edge_threshold: float = 1e-3,
    seed: int = 0,
) -> list[SweepPoint]:
    """Run the bounded v0.1 graph sweep used by the benchmark CLI."""
    rows: list[SweepPoint] = []
    for index, eta in enumerate(etas):
        eta = float(eta)
        a = floquet_rabi_adjacency(nmax=nmax, eta=eta)
        lap = normalized_magnetic_laplacian(a)
        spectrum = np.linalg.eigvalsh(lap)
        q2 = sample_loop_statistics(
            nmax, eta, q=2, samples=loop_samples,
            rel_edge_threshold=rel_edge_threshold, seed=seed + 10 * index + 2,
        )
        q3 = sample_loop_statistics(
            nmax, eta, q=3, samples=loop_samples,
            rel_edge_threshold=rel_edge_threshold, seed=seed + 10 * index + 3,
        )
        q4 = sample_loop_statistics(
            nmax, eta, q=4, samples=loop_samples,
            rel_edge_threshold=rel_edge_threshold, seed=seed + 10 * index + 4,
        )
        rows.append(
            SweepPoint(
                eta=eta,
                lambda1=float(spectrum[0]),
                lambda_max=float(spectrum[-1]),
                laplacian_hermiticity_error=float(np.max(np.abs(lap - lap.conj().T))),
                gauge_spectrum_error=gauge_spectrum_residual(
                    nmax=nmax, eta=eta, seed=seed + index
                ),
                q2_frustrated_fraction=q2.frustrated_fraction,
                q3_frustrated_fraction=q3.frustrated_fraction,
                q4_frustrated_fraction=q4.frustrated_fraction,
            )
        )
    return rows

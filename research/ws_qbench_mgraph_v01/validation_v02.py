"""WS-QBENCH-MGRAPH v0.2 validation and ablation diagnostics.

This module extends the v0.1 magnetic-graph harness with paper-aligned
random-subgraph conductance, loop-formation probabilities, cutoff convergence,
and threshold-sensitivity diagnostics.

Claim ceiling:
- IMPLEMENTED IN SOFTWARE
- SIMULATED ONLY
- SUPPORTED BY LITERATURE
- REQUIRES INDEPENDENT NUMERICAL REPRODUCTION

The source paper does not specify the numerical rule used to treat very small
nonzero hopping weights as disconnected in Supplementary Note S1. Therefore
``rel_edge_threshold`` remains an explicit sensitivity parameter. Results that
materially depend on that threshold must not be described as a reproduction of
Supplementary Figure S1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Sequence

import numpy as np

from .magnetic_graph import floquet_rabi_hopping, lambda1_metric


@dataclass(frozen=True)
class CutoffPoint:
    eta: float
    nmax: int
    lambda1: float
    reference_nmax: int
    reference_lambda1: float
    absolute_error: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class WeakCouplingPoint:
    eta: float
    lambda1: float
    asymptote_2eta: float
    absolute_error: float
    relative_error: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class SubgraphEnsembleStats:
    eta: float
    q: int
    requested_samples: int
    conductance_mean: float
    conductance_std: float
    p_connect: float
    p_nontrivial: float
    p_trivial: float
    conditional_nontrivial: float
    mean_nontrivial_strength: float
    mean_trivial_strength: float
    max_phase_quantization_error: float
    rel_edge_threshold: float
    absolute_edge_threshold: float
    complete_bipartite_null: float
    conductance_excess_over_null: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _validate_nodes(nodes: Sequence[int], dim: int, name: str) -> np.ndarray:
    arr = np.asarray(nodes, dtype=int)
    if arr.ndim != 1 or len(arr) == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional sequence")
    if np.any(arr < 0) or np.any(arr >= dim):
        raise ValueError(f"{name} contains an out-of-range node")
    if len(np.unique(arr)) != len(arr):
        raise ValueError(f"{name} must contain distinct nodes")
    return arr


def subgraph_conductance_from_hopping(
    hopping: np.ndarray,
    plus_nodes: Sequence[int],
    minus_nodes: Sequence[int],
) -> float:
    """Return the paper's weighted separation cost C_q for one bipartite subgraph.

    The numerator is the total absolute edge weight crossing from the selected
    2q-node subgraph to its complement. The denominator is the volume of the
    selected subgraph, i.e. the sum of full-graph weighted node degrees.
    """
    k = np.asarray(hopping, dtype=np.complex128)
    if k.ndim != 2 or k.shape[0] != k.shape[1]:
        raise ValueError("hopping must be a square matrix")
    dim = k.shape[0]
    plus = _validate_nodes(plus_nodes, dim, "plus_nodes")
    minus = _validate_nodes(minus_nodes, dim, "minus_nodes")
    if len(plus) != len(minus):
        raise ValueError("plus_nodes and minus_nodes must have equal length")

    weights = np.abs(k)
    plus_degree = np.sum(weights, axis=1)
    minus_degree = np.sum(weights, axis=0)
    volume = float(np.sum(plus_degree[plus]) + np.sum(minus_degree[minus]))
    if volume <= 0.0:
        raise ValueError("selected subgraph has zero weighted volume")

    internal_once = float(np.sum(weights[np.ix_(plus, minus)]))
    boundary = volume - 2.0 * internal_once
    if boundary < 0.0 and abs(boundary) < 1e-13 * volume:
        boundary = 0.0
    if boundary < 0.0:
        raise ValueError("computed negative boundary weight")
    return boundary / volume


def _loop_product(
    hopping: np.ndarray,
    plus_nodes: np.ndarray,
    minus_nodes: np.ndarray,
) -> complex:
    q = len(plus_nodes)
    product = 1.0 + 0.0j
    for r in range(q):
        p_here = int(plus_nodes[r])
        p_next = int(plus_nodes[(r + 1) % q])
        m_here = int(minus_nodes[r])
        product *= hopping[p_here, m_here] * np.conj(hopping[p_next, m_here])
    return product


def _loop_edge_values(
    hopping: np.ndarray,
    plus_nodes: np.ndarray,
    minus_nodes: np.ndarray,
) -> list[complex]:
    q = len(plus_nodes)
    edges: list[complex] = []
    for r in range(q):
        p_here = int(plus_nodes[r])
        p_next = int(plus_nodes[(r + 1) % q])
        m_here = int(minus_nodes[r])
        edges.extend((hopping[p_here, m_here], hopping[p_next, m_here]))
    return edges


def _phase_quantization_error(product: complex) -> float:
    """Distance of arg(product) from the expected {0, pi} phase set."""
    if product == 0.0:
        return 0.0
    phase = math.atan2(product.imag, product.real)
    return min(abs(phase), abs(abs(phase) - math.pi))


def complete_bipartite_null_conductance(nmax: int, q: int) -> float:
    """Exact C_q for a complete unweighted bipartite graph with equal partitions.

    This is a Worldshepherd adversarial/null control, not a source-paper
    observable. For partition size d=nmax+1 and q selected nodes on each side,
    every selected node has degree d, the boundary has 2q(d-q) unit edges,
    and the selected volume is 2qd; hence C_q = 1 - q/d.
    """
    dim = nmax + 1
    if nmax < 1 or q < 1 or q > dim:
        raise ValueError("require nmax >= 1 and 1 <= q <= nmax + 1")
    return 1.0 - q / dim


def sample_random_subgraphs(
    nmax: int,
    eta: float,
    q: int,
    samples: int = 20_000,
    rel_edge_threshold: float = 1e-3,
    seed: int = 9675,
) -> SubgraphEnsembleStats:
    """Sample the random 2q-node subgraphs used for C_q and W_q diagnostics.

    Number states are sampled uniformly without replacement within each
    bipartition, matching the interpretation of a 2q-node subgraph. A loop is
    treated as connected only when all 2q loop edges exceed the explicit
    relative threshold. This threshold is a Worldshepherd numerical convention,
    not a claimed source-paper constant.
    """
    if nmax < 1:
        raise ValueError("nmax must be >= 1")
    dim = nmax + 1
    if q < 2 or q > dim:
        raise ValueError("q must satisfy 2 <= q <= nmax + 1")
    if samples <= 0:
        raise ValueError("samples must be positive")
    if not (0.0 <= rel_edge_threshold < 1.0):
        raise ValueError("rel_edge_threshold must be in [0,1)")

    hopping = floquet_rabi_hopping(nmax=nmax, eta=float(eta))
    absolute_threshold = float(rel_edge_threshold * np.max(np.abs(hopping)))
    rng = np.random.default_rng(seed)

    conductances = np.empty(samples, dtype=float)
    connected = 0
    nontrivial = 0
    trivial = 0
    nontrivial_strengths: list[float] = []
    trivial_strengths: list[float] = []
    max_phase_error = 0.0

    for index in range(samples):
        plus = rng.choice(dim, size=q, replace=False)
        minus = rng.choice(dim, size=q, replace=False)
        conductances[index] = subgraph_conductance_from_hopping(hopping, plus, minus)

        edges = _loop_edge_values(hopping, plus, minus)
        if any(abs(edge) <= absolute_threshold for edge in edges):
            continue

        product = _loop_product(hopping, plus, minus)
        if product == 0.0:
            continue
        connected += 1
        max_phase_error = max(max_phase_error, _phase_quantization_error(product))
        strength = float(abs(product) ** (1.0 / (2.0 * q)))
        if product.real < 0.0:
            nontrivial += 1
            nontrivial_strengths.append(strength)
        else:
            trivial += 1
            trivial_strengths.append(strength)

    p_connect = connected / samples
    null_conductance = complete_bipartite_null_conductance(nmax, q)
    p_nontrivial = nontrivial / samples
    p_trivial = trivial / samples
    conditional_nontrivial = nontrivial / connected if connected else 0.0

    return SubgraphEnsembleStats(
        eta=float(eta),
        q=q,
        requested_samples=samples,
        conductance_mean=float(np.mean(conductances)),
        conductance_std=float(np.std(conductances, ddof=0)),
        p_connect=p_connect,
        p_nontrivial=p_nontrivial,
        p_trivial=p_trivial,
        conditional_nontrivial=conditional_nontrivial,
        mean_nontrivial_strength=(
            float(np.mean(nontrivial_strengths)) if nontrivial_strengths else 0.0
        ),
        mean_trivial_strength=(
            float(np.mean(trivial_strengths)) if trivial_strengths else 0.0
        ),
        max_phase_quantization_error=max_phase_error,
        rel_edge_threshold=rel_edge_threshold,
        absolute_edge_threshold=absolute_threshold,
        complete_bipartite_null=null_conductance,
        conductance_excess_over_null=float(np.mean(conductances)) - null_conductance,
    )


def cutoff_convergence(
    eta: float,
    nmax_values: Iterable[int] = (32, 64, 100, 150, 200),
) -> list[CutoffPoint]:
    """Compare lambda1 across Fock cutoffs using the largest cutoff as reference."""
    values = tuple(int(value) for value in nmax_values)
    if not values:
        raise ValueError("nmax_values must not be empty")
    if any(value < 1 for value in values):
        raise ValueError("all nmax values must be >= 1")
    if sorted(set(values)) != list(values):
        raise ValueError("nmax_values must be strictly increasing and unique")

    computed = [(nmax, lambda1_metric(nmax=nmax, eta=float(eta))) for nmax in values]
    reference_nmax, reference_lambda1 = computed[-1]
    return [
        CutoffPoint(
            eta=float(eta),
            nmax=nmax,
            lambda1=value,
            reference_nmax=reference_nmax,
            reference_lambda1=reference_lambda1,
            absolute_error=abs(value - reference_lambda1),
        )
        for nmax, value in computed
    ]


def weak_coupling_diagnostics(
    etas: Iterable[float] = (0.001, 0.005, 0.01, 0.02),
    nmax: int = 200,
) -> list[WeakCouplingPoint]:
    """Measure deviation from the paper's weak-coupling asymptote lambda1 ~ 2 eta."""
    rows: list[WeakCouplingPoint] = []
    for eta in etas:
        eta = float(eta)
        if eta <= 0.0:
            raise ValueError("weak-coupling etas must be positive")
        value = lambda1_metric(nmax=nmax, eta=eta)
        asymptote = 2.0 * eta
        error = abs(value - asymptote)
        rows.append(
            WeakCouplingPoint(
                eta=eta,
                lambda1=value,
                asymptote_2eta=asymptote,
                absolute_error=error,
                relative_error=error / asymptote,
            )
        )
    return rows


def threshold_sensitivity(
    eta: float,
    q: int,
    thresholds: Iterable[float] = (1e-2, 1e-3, 1e-4, 1e-5, 1e-6),
    nmax: int = 200,
    samples: int = 5_000,
    seed: int = 9675,
) -> list[SubgraphEnsembleStats]:
    """Expose dependence of loop statistics on the unresolved edge-zero convention."""
    return [
        sample_random_subgraphs(
            nmax=nmax,
            eta=eta,
            q=q,
            samples=samples,
            rel_edge_threshold=float(threshold),
            seed=seed,
        )
        for threshold in thresholds
    ]

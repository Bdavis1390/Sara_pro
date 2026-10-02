"""WS-QBENCH-MGRAPH v0.9 loop-zero-semantics audit.

This module applies the corresponding-author loop convention literally to the
repository's numerically stable closed-form displacement matrix:

- Nmax=200
- q number states sampled without replacement in each bipartition
- no edge threshold and no hopping-order cutoff
- connected iff the 2q-fold loop product is exactly nonzero in float64
- phase classes within 1e-9 of 0 or pi

The purpose is not to claim Supplementary Figure S1 reproduction.  It is to
test whether the author-stated rule plus our stable implementation is already
sufficient to recover the published loop-formation behavior.  Any mismatch is
retained as evidence that Code S1's concrete floating-point implementation is
still required.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np

from .magnetic_graph import _loop_product, floquet_rabi_hopping


@dataclass(frozen=True)
class LoopProbabilityAudit:
    eta: float
    q: int
    nmax: int
    realizations: int
    connected: int
    nontrivial: int
    trivial: int
    unclassified_connected: int
    p_connect: float
    p_nontrivial: float
    p_trivial: float
    nontrivial_fraction_given_connected: float
    binomial_se_p_connect: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def classify_phase(product: complex, tolerance: float = 1e-9) -> str | None:
    """Classify one nonzero loop product under the author-stated convention."""
    z = complex(product)
    if z == 0.0:
        return None
    phi = math.atan2(z.imag, z.real)
    if phi < 0.0:
        phi += 2.0 * math.pi
    if abs(phi - math.pi) < tolerance:
        return "nontrivial"
    if min(abs(phi), abs(phi - 2.0 * math.pi)) < tolerance:
        return "trivial"
    return "unclassified"


def loop_probability_audit(
    eta: float,
    q: int,
    *,
    nmax: int = 200,
    realizations: int = 20_000,
    seed: int = 9675,
    tolerance: float = 1e-9,
) -> LoopProbabilityAudit:
    """Monte Carlo audit using no threshold proxy.

    Sampling is without replacement within each bipartition.  The returned
    probabilities are over *all* realizations, so p_connect should equal
    p_nontrivial + p_trivial whenever no connected loop is unclassified.
    """
    if eta < 0.0:
        raise ValueError("eta must be non-negative")
    if nmax < 1:
        raise ValueError("nmax must be positive")
    if q < 2 or q > nmax + 1:
        raise ValueError("q must satisfy 2 <= q <= nmax+1")
    if realizations <= 0:
        raise ValueError("realizations must be positive")

    hopping = floquet_rabi_hopping(nmax=nmax, eta=float(eta), h_perp=1.0)
    rng = np.random.default_rng(seed)

    connected = nontrivial = trivial = unclassified = 0
    for _ in range(realizations):
        plus_nodes = rng.choice(nmax + 1, size=q, replace=False)
        minus_nodes = rng.choice(nmax + 1, size=q, replace=False)
        product = _loop_product(hopping, plus_nodes, minus_nodes)
        label = classify_phase(product, tolerance=tolerance)
        if label is None:
            continue
        connected += 1
        if label == "nontrivial":
            nontrivial += 1
        elif label == "trivial":
            trivial += 1
        else:
            unclassified += 1

    p_connect = connected / realizations
    p_nontrivial = nontrivial / realizations
    p_trivial = trivial / realizations
    conditional = nontrivial / connected if connected else 0.0
    se = math.sqrt(p_connect * (1.0 - p_connect) / realizations)

    return LoopProbabilityAudit(
        eta=float(eta),
        q=int(q),
        nmax=int(nmax),
        realizations=int(realizations),
        connected=connected,
        nontrivial=nontrivial,
        trivial=trivial,
        unclassified_connected=unclassified,
        p_connect=float(p_connect),
        p_nontrivial=float(p_nontrivial),
        p_trivial=float(p_trivial),
        nontrivial_fraction_given_connected=float(conditional),
        binomial_se_p_connect=float(se),
    )


def probability_identity_residual(row: LoopProbabilityAudit) -> float:
    """Return pConnect - (pNontrivial + pTrivial)."""
    return float(row.p_connect - row.p_nontrivial - row.p_trivial)

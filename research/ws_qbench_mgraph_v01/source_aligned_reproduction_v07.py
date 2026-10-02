"""Author-aligned WS-QBENCH-MGRAPH v0.7 reproduction primitives.

The numerical conventions in this module are locked from the corresponding
author's clarification. Exact Figure 4/S1 reproduction remains blocked until
Code S1 is locally acquired and verified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np

from .localization_ablation_v04 import source_localization
from .magnetic_graph import _loop_product, floquet_rabi_hopping


@dataclass(frozen=True)
class AuthorLockedParameters:
    nmax: int = 200
    realizations: int = 20_000
    q_values: tuple[int, ...] = tuple(range(2, 11)) + (30, 50)
    phase_tolerance: float = 1e-9
    hbar: float = 1.0
    omega0: float = 1.0
    h0: float = 0.0
    h_parallel: float = 0.0
    h_perp: float = 0.5
    eigenstates: int = 30

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AuthorLoopStats:
    q: int
    realizations: int
    connected: int
    nontrivial: int
    trivial: int
    unclassified_connected: int
    p_connect: float
    p_nontrivial: float
    p_trivial: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def classify_author_loop_product(
    product: complex,
    *,
    phase_tolerance: float = 1e-9,
) -> tuple[bool, str | None]:
    """Apply the corresponding-author loop convention.

    Connectivity uses exact floating-point nonzero. Phase is represented on
    [0, 2*pi) before applying the author's 0/pi tolerances.
    """
    value = complex(product)
    if value == 0.0:
        return False, None

    phi = math.atan2(value.imag, value.real)
    if phi < 0.0:
        phi += 2.0 * math.pi

    if abs(phi - math.pi) < phase_tolerance:
        return True, "nontrivial"
    if min(abs(phi), abs(phi - 2.0 * math.pi)) < phase_tolerance:
        return True, "trivial"
    return True, "unclassified"


def source_aligned_loop_statistics(
    eta: float,
    q: int,
    *,
    nmax: int = 200,
    realizations: int = 20_000,
    seed: int = 9675,
    phase_tolerance: float = 1e-9,
) -> AuthorLoopStats:
    """Monte Carlo loop statistics with no threshold proxy and no replacement."""
    if nmax < 1:
        raise ValueError("nmax must be positive")
    dim = nmax + 1
    if q < 2 or q > dim:
        raise ValueError("q must satisfy 2 <= q <= nmax+1")
    if realizations <= 0:
        raise ValueError("realizations must be positive")

    hopping = floquet_rabi_hopping(nmax=nmax, eta=float(eta), h_perp=1.0)
    rng = np.random.default_rng(seed)

    connected = nontrivial = trivial = unclassified = 0
    for _ in range(realizations):
        plus_nodes = rng.choice(dim, size=q, replace=False)
        minus_nodes = rng.choice(dim, size=q, replace=False)
        product = _loop_product(hopping, plus_nodes, minus_nodes)
        is_connected, label = classify_author_loop_product(
            product, phase_tolerance=phase_tolerance
        )
        if not is_connected:
            continue
        connected += 1
        if label == "nontrivial":
            nontrivial += 1
        elif label == "trivial":
            trivial += 1
        else:
            unclassified += 1

    return AuthorLoopStats(
        q=q,
        realizations=realizations,
        connected=connected,
        nontrivial=nontrivial,
        trivial=trivial,
        unclassified_connected=unclassified,
        p_connect=connected / realizations,
        p_nontrivial=nontrivial / realizations,
        p_trivial=trivial / realizations,
    )


def source_aligned_figure4ef_ipr(eta: float, *, nmax: int = 200):
    """Return the first-30-state IPR summary at the author-locked normalization."""
    return source_localization(
        nmax=nmax,
        eta=float(eta),
        omega0=1.0,
        h_perp=0.5,
        h_parallel=0.0,
        h0=0.0,
        eigenstates=30,
    )

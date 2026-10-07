"""Single-excitation, four-state Lindblad model in hbar=1 dimensionless units.

Basis: |A>, |P> (one shared phonon), |B>, |loss> (absorbing state).

H = Δ_A |A><A| + Δ_P |P><P| + Δ_B |B><B|
    + g_A (|A><P| + h.c.)
    + g_B (e^{i φ}|P><B| + h.c.)
Collapse operators:
    sqrt(kappa) |loss><P|
    sqrt(gamma_j) |j><j|, j=A,P,B

The Lindblad generator is completely positive and trace-preserving.
This is a *phenomenological toy*; it is neither a continuum phononic
waveguide calculation nor a faithful simulation of the cited papers.
"""
from dataclasses import dataclass, fields
import math
import numpy as np
from scipy.linalg import expm

LABELS = ("qubit_a", "phonon", "qubit_b", "environment_loss")
DIM = 4

@dataclass(frozen=True)
class Model:
    g_a: float = 1.0
    g_b: float = 1.0
    detuning_a: float = 0.0
    detuning_phonon: float = 0.0
    detuning_b: float = 0.0
    phase: float = 0.0
    kappa: float = 0.0
    gamma_a: float = 0.0
    gamma_phonon: float = 0.0
    gamma_b: float = 0.0

    def __post_init__(self):
        for field in fields(self):
            val = getattr(self, field.name)
            if not isinstance(val, (float, int, np.floating, np.integer)) or not math.isfinite(val):
                raise ValueError(f"{field.name} must be a finite real number")
            if field.name in {"g_a", "g_b", "kappa", "gamma_a", "gamma_phonon", "gamma_b"} and val < 0:
                raise ValueError(f"{field.name} cannot be negative")


def ideal_swap_time(g: float = 1.0) -> float:
    if not math.isfinite(g) or g <= 0:
        raise ValueError("g must be finite and positive")
    return math.pi / (math.sqrt(2) * g)


def hamiltonian(m: Model) -> np.ndarray:
    h = np.diag([m.detuning_a, m.detuning_phonon, m.detuning_b, 0]).astype(complex)
    h[0, 1] = h[1, 0] = m.g_a
    h[1, 2] = m.g_b * np.exp(1j * m.phase)
    h[2, 1] = np.conj(h[1, 2])
    return h


def collapse_operators(m: Model) -> list[np.ndarray]:
    ops = []
    if m.kappa:
        c = np.zeros((DIM, DIM), complex)
        c[3, 1] = math.sqrt(m.kappa)
        ops.append(c)
    for j, rate in [(0, m.gamma_a), (1, m.gamma_phonon), (2, m.gamma_b)]:
        if rate:
            c = np.zeros((DIM, DIM), complex)
            c[j, j] = math.sqrt(rate)
            ops.append(c)
    return ops


def liouvillian(m: Model) -> np.ndarray:
    """Fortran vec convention: vec(A rho B) = (B^T tensor A) vec(rho)."""
    h = hamiltonian(m)
    eye = np.eye(DIM, dtype=complex)
    gen = -1j * (np.kron(eye, h) - np.kron(h.T, eye))
    for c in collapse_operators(m):
        cd_c = c.conj().T @ c
        gen += np.kron(c.conj(), c) - 0.5 * (
            np.kron(eye, cd_c) + np.kron(cd_c.T, eye)
        )
    return gen


def density_at(m: Model, t: float, rho0: np.ndarray | None = None) -> np.ndarray:
    if not math.isfinite(t) or t < 0:
        raise ValueError("Time must be nonnegative and finite")
    if rho0 is None:
        rho0 = np.zeros((DIM, DIM), dtype=complex)
        rho0[0, 0] = 1.0
    rho0 = np.asarray(rho0, complex)
    if rho0.shape != (DIM, DIM) or not np.all(np.isfinite(rho0)):
        raise ValueError("rho0 must be a finite 4x4 matrix")
    if np.max(np.abs(rho0 - rho0.conj().T)) > 1e-10 or abs(np.trace(rho0) - 1) > 1e-10 or np.min(np.linalg.eigvalsh(rho0)) < -1e-10:
        raise ValueError("rho0 must be a valid density matrix")
    v = expm(liouvillian(m) * t) @ rho0.reshape(-1, order="F")
    return v.reshape((DIM, DIM), order="F")


def metrics(rho: np.ndarray) -> dict:
    """Unconditional probabilities; loss is counted (not postselected out)."""
    pops = np.real(np.diag(rho))
    output = {name: float(val) for name, val in zip(LABELS, pops)}
    output["trace"] = float(np.real(np.trace(rho)))
    output["min_eigenvalue"] = float(np.min(np.linalg.eigvalsh((rho + rho.conj().T) / 2)))
    output["coherence_a_b_magnitude"] = float(abs(rho[0, 2]))
    return output


def attenuated_coupling(g: float, d_over_length: float) -> float:
    """Ad hoc amplitude attenuation, NOT a calibrated Ge/Si device relation."""
    if not math.isfinite(g) or g < 0 or not math.isfinite(d_over_length) or d_over_length < 0:
        raise ValueError("g and d_over_length must be finite and nonnegative")
    return g * math.exp(-d_over_length / 2)

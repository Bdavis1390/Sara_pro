"""Finite multimode phonon-bus Lindblad model for Worldshepherd QPHONON v0.3.

The model keeps a vacuum state, sender excitation, N single-phonon mode states,
and receiver excitation. It therefore supports sender->receiver single-qubit channel
metrics including vacuum/excitation coherence. Finite-temperature upward phonon
jumps are available only as a low-occupation single-excitation approximation.

This is a phenomenological research model, not a finite-element or fabricated-device
model and not a reproduction of any source-paper figure.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import expm1, isfinite, pi
import numpy as np
from scipy.linalg import expm

H_PLANCK = 6.62607015e-34
K_BOLTZMANN = 1.380649e-23


def bose_occupation(frequency_hz: float, temperature_k: float) -> float:
    """Mean Bose occupation 1/(exp(h f/kT)-1), stable for low temperature."""
    if not isfinite(frequency_hz) or frequency_hz <= 0:
        raise ValueError("frequency_hz must be finite and positive")
    if not isfinite(temperature_k) or temperature_k < 0:
        raise ValueError("temperature_k must be finite and nonnegative")
    if temperature_k == 0:
        return 0.0
    x = H_PLANCK * frequency_hz / (K_BOLTZMANN * temperature_k)
    if x > 745:
        return 0.0
    return 1.0 / expm1(x)


def propagation_delay_s(distance_m: float, group_velocity_m_s: float) -> float:
    if not isfinite(distance_m) or distance_m < 0:
        raise ValueError("distance_m must be finite and nonnegative")
    if not isfinite(group_velocity_m_s) or group_velocity_m_s <= 0:
        raise ValueError("group_velocity_m_s must be finite and positive")
    return distance_m / group_velocity_m_s


def propagation_phase_rad(frequency_hz: float, distance_m: float,
                          group_velocity_m_s: float, phase_offset_rad: float = 0.0) -> float:
    if not isfinite(phase_offset_rad):
        raise ValueError("phase_offset_rad must be finite")
    tau = propagation_delay_s(distance_m, group_velocity_m_s)
    return float((2*pi*frequency_hz*tau + phase_offset_rad) % (2*pi))


@dataclass(frozen=True)
class Mode:
    frequency_hz: float
    detuning_hz: float
    coupling_a_hz: float
    coupling_b_hz: float
    quality_factor: float
    phase_rad: float = 0.0

    def __post_init__(self):
        vals = (self.frequency_hz, self.detuning_hz, self.coupling_a_hz,
                self.coupling_b_hz, self.quality_factor, self.phase_rad)
        if any(not isfinite(v) for v in vals):
            raise ValueError("all mode parameters must be finite")
        if self.frequency_hz <= 0 or self.quality_factor <= 0:
            raise ValueError("frequency and quality_factor must be positive")
        if self.coupling_a_hz < 0 or self.coupling_b_hz < 0:
            raise ValueError("couplings must be nonnegative")

    @property
    def kappa_rad_s(self) -> float:
        return 2*pi*self.frequency_hz/self.quality_factor


@dataclass(frozen=True)
class MultiModeModel:
    modes: tuple[Mode, ...]
    temperature_k: float = 0.0
    detuning_a_hz: float = 0.0
    detuning_b_hz: float = 0.0
    gamma_phi_a_s_inv: float = 0.0
    gamma_phi_b_s_inv: float = 0.0
    thermal_occupation_limit: float = 0.05
    allow_high_thermal: bool = False

    def __post_init__(self):
        if not self.modes:
            raise ValueError("at least one phonon mode is required")
        for v in (self.temperature_k, self.detuning_a_hz, self.detuning_b_hz,
                  self.gamma_phi_a_s_inv, self.gamma_phi_b_s_inv,
                  self.thermal_occupation_limit):
            if not isfinite(v):
                raise ValueError("model parameters must be finite")
        if self.temperature_k < 0 or self.gamma_phi_a_s_inv < 0 or self.gamma_phi_b_s_inv < 0:
            raise ValueError("temperature and dephasing rates must be nonnegative")
        if self.thermal_occupation_limit <= 0:
            raise ValueError("thermal_occupation_limit must be positive")
        max_n = max(self.thermal_occupations())
        if max_n > self.thermal_occupation_limit and not self.allow_high_thermal:
            raise ValueError(
                f"max thermal occupation {max_n:.6g} exceeds single-excitation limit "
                f"{self.thermal_occupation_limit}; use a larger Fock model or explicit override"
            )

    @property
    def dim(self) -> int:
        return len(self.modes) + 3

    @property
    def idx_vac(self) -> int:
        return 0

    @property
    def idx_a(self) -> int:
        return 1

    @property
    def idx_b(self) -> int:
        return self.dim - 1

    def idx_mode(self, mode_index: int) -> int:
        if not 0 <= mode_index < len(self.modes):
            raise IndexError(mode_index)
        return 2 + mode_index

    def thermal_occupations(self) -> tuple[float, ...]:
        return tuple(bose_occupation(m.frequency_hz, self.temperature_k) for m in self.modes)


def hamiltonian(model: MultiModeModel) -> np.ndarray:
    d = model.dim
    h = np.zeros((d, d), dtype=complex)
    h[model.idx_a, model.idx_a] = 2*pi*model.detuning_a_hz
    h[model.idx_b, model.idx_b] = 2*pi*model.detuning_b_hz
    for i, mode in enumerate(model.modes):
        j = model.idx_mode(i)
        h[j, j] = 2*pi*mode.detuning_hz
        ga = 2*pi*mode.coupling_a_hz
        gb = 2*pi*mode.coupling_b_hz * np.exp(1j*mode.phase_rad)
        h[model.idx_a, j] = ga
        h[j, model.idx_a] = ga
        h[j, model.idx_b] = gb
        h[model.idx_b, j] = np.conj(gb)
    return h


def collapse_operators(model: MultiModeModel) -> list[np.ndarray]:
    d = model.dim
    ops: list[np.ndarray] = []
    for i, (mode, nbar) in enumerate(zip(model.modes, model.thermal_occupations())):
        j = model.idx_mode(i)
        down = np.zeros((d, d), dtype=complex)
        down[model.idx_vac, j] = np.sqrt(mode.kappa_rad_s * (nbar + 1.0))
        ops.append(down)
        if nbar > 0:
            up = np.zeros((d, d), dtype=complex)
            up[j, model.idx_vac] = np.sqrt(mode.kappa_rad_s * nbar)
            ops.append(up)
    for idx, gamma_s_inv in ((model.idx_a, model.gamma_phi_a_s_inv),
                              (model.idx_b, model.gamma_phi_b_s_inv)):
        if gamma_s_inv > 0:
            c = np.zeros((d, d), dtype=complex)
            # Projector Lindblad with coefficient sqrt(2 gamma) gives
            # an isolated |1><0| coherence decay rate gamma.
            c[idx, idx] = np.sqrt(2*gamma_s_inv)
            ops.append(c)
    return ops


def liouvillian(model: MultiModeModel) -> np.ndarray:
    h = hamiltonian(model)
    d = model.dim
    eye = np.eye(d, dtype=complex)
    gen = -1j*(np.kron(eye, h) - np.kron(h.T, eye))
    for c in collapse_operators(model):
        cdc = c.conj().T @ c
        gen += np.kron(c.conj(), c) - 0.5*(np.kron(eye, cdc) + np.kron(cdc.T, eye))
    return gen


def initial_qubit_density(model: MultiModeModel, alpha: complex, beta: complex) -> np.ndarray:
    if not all(np.isfinite([alpha.real, alpha.imag, beta.real, beta.imag])):
        raise ValueError("input amplitudes must be finite")
    norm = abs(alpha)**2 + abs(beta)**2
    if abs(norm - 1.0) > 1e-10:
        raise ValueError("input amplitudes must be normalized")
    psi = np.zeros(model.dim, dtype=complex)
    psi[model.idx_vac] = alpha
    psi[model.idx_a] = beta
    return np.outer(psi, psi.conj())


def evolve(model: MultiModeModel, rho0: np.ndarray, time_s: float) -> np.ndarray:
    if not isfinite(time_s) or time_s < 0:
        raise ValueError("time_s must be finite and nonnegative")
    rho0 = np.asarray(rho0, dtype=complex)
    if rho0.shape != (model.dim, model.dim):
        raise ValueError("rho0 shape does not match model dimension")
    if not np.all(np.isfinite(rho0)):
        raise ValueError("rho0 must be finite")
    if np.max(np.abs(rho0-rho0.conj().T)) > 1e-10:
        raise ValueError("rho0 must be Hermitian")
    if abs(np.trace(rho0)-1) > 1e-10 or np.min(np.linalg.eigvalsh(rho0)) < -1e-10:
        raise ValueError("rho0 must be a valid density matrix")
    prop = expm(liouvillian(model)*time_s)
    out = prop @ rho0.reshape(-1, order="F")
    return out.reshape((model.dim, model.dim), order="F")


def receiver_reduced(model: MultiModeModel, rho: np.ndarray) -> np.ndarray:
    """Trace sender/modes out, retaining receiver qubit |0>,|1> coherence."""
    rho = np.asarray(rho, dtype=complex)
    if rho.shape != (model.dim, model.dim):
        raise ValueError("rho shape does not match model dimension")
    p1 = float(np.real(rho[model.idx_b, model.idx_b]))
    c01 = rho[model.idx_vac, model.idx_b]
    out = np.array([[1.0-p1, c01], [np.conj(c01), p1]], dtype=complex)
    return (out + out.conj().T)/2


CARDINAL_STATES: tuple[tuple[str, complex, complex], ...] = (
    ("0", 1, 0),
    ("1", 0, 1),
    ("+", 1/np.sqrt(2), 1/np.sqrt(2)),
    ("-", 1/np.sqrt(2), -1/np.sqrt(2)),
    ("+i", 1/np.sqrt(2), 1j/np.sqrt(2)),
    ("-i", 1/np.sqrt(2), -1j/np.sqrt(2)),
)


def channel_outputs(model: MultiModeModel, time_s: float) -> dict[str, np.ndarray]:
    prop = expm(liouvillian(model)*time_s)
    outputs: dict[str, np.ndarray] = {}
    for name, alpha, beta in CARDINAL_STATES:
        rho0 = initial_qubit_density(model, alpha, beta)
        vec = prop @ rho0.reshape(-1, order="F")
        outputs[name] = receiver_reduced(model, vec.reshape((model.dim, model.dim), order="F"))
    return outputs


def _state_fidelity_pure(rho: np.ndarray, alpha: complex, beta: complex,
                         correction_phase_rad: float = 0.0) -> float:
    target = np.array([alpha, beta], dtype=complex)
    u = np.diag([1.0, np.exp(-1j*correction_phase_rad)])
    corrected = u @ rho @ u.conj().T
    val = np.real(target.conj() @ corrected @ target)
    return float(np.clip(val, 0.0, 1.0))


def six_state_average_fidelity(model: MultiModeModel, time_s: float,
                               correction_phase_rad: float = 0.0) -> float:
    outputs = channel_outputs(model, time_s)
    vals = [_state_fidelity_pure(outputs[name], a, b, correction_phase_rad)
            for name, a, b in CARDINAL_STATES]
    return float(np.mean(vals))


def best_phase_corrected_fidelity(model: MultiModeModel, time_s: float,
                                  phase_points: int = 181) -> dict[str, float]:
    if not isinstance(phase_points, int) or phase_points < 3:
        raise ValueError("phase_points must be integer >= 3")
    outputs = channel_outputs(model, time_s)
    phases = np.linspace(-pi, pi, phase_points)
    vals = []
    for phase in phases:
        fs = [_state_fidelity_pure(outputs[name], a, b, float(phase))
              for name, a, b in CARDINAL_STATES]
        vals.append(float(np.mean(fs)))
    i = int(np.argmax(vals))
    raw = np.mean([_state_fidelity_pure(outputs[name], a, b, 0.0)
                   for name, a, b in CARDINAL_STATES])
    return {"raw_six_state_fidelity": float(raw),
            "phase_corrected_six_state_fidelity": vals[i],
            "best_receiver_z_phase_rad": float(phases[i])}


def state_metrics(rho: np.ndarray) -> dict[str, float]:
    rho = np.asarray(rho, dtype=complex)
    return {
        "trace_error": float(abs(np.trace(rho)-1.0)),
        "minimum_eigenvalue": float(np.min(np.linalg.eigvalsh((rho+rho.conj().T)/2))),
    }


def paper_parameter_context() -> dict[str, object]:
    """Ranges stated in Myronov et al. 2026; not measured by Worldshepherd."""
    return {
        "source_doi": "10.1063/5.0332643",
        "phonon_frequency_ghz_range": [10.0, 50.0],
        "estimated_spin_phonon_coupling_mhz_range": [0.1, 10.0],
        "quality_factor_range": [1e4, 1e6],
        "spin_T2_star_us_range": [1.0, 10.0],
        "qw_thickness_nm_range_textual": [10.0, 30.0],
        "phonon_wavelength_nm_range_textual": [100.0, 500.0],
        "coherent_propagation_length_textual": "tens of micrometers to centimeters expected; not experimentally validated by this model",
        "classification": "SUPPORTED BY LITERATURE / NOT WORLD SHEPHERD LAB DATA",
    }

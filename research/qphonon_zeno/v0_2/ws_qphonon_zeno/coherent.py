"""Counterintuitive adiabatic transport and site-monitoring baselines.

A four-state Lindblad toy model: |A>, |P>, |B>, |loss>. Units hbar=1;
all rates and times dimensionless. No continuum phonon, engineered material,
thermal reservoir, or cosmological quantum field is represented.
"""
from dataclasses import dataclass
from math import exp, isfinite
import numpy as np
from scipy.integrate import solve_ivp, trapezoid
from .model import Model, density_at, liouvillian, metrics


@dataclass(frozen=True)
class Pulse:
    duration: float = 16.0
    peak: float = 1.0
    center_early: float = 0.33
    center_late: float = 0.67
    sigma: float = 0.17

    def __post_init__(self):
        if any(not isfinite(v) for v in (self.duration, self.peak, self.center_early,
                                          self.center_late, self.sigma)):
            raise ValueError('Pulse values must be finite')
        if self.duration <= 0 or self.peak < 0 or self.sigma <= 0:
            raise ValueError('Duration and sigma must be positive, peak nonnegative')
        if not 0 < self.center_early < self.center_late < 1:
            raise ValueError('Pulse must follow counterintuitive time ordering')

    def couplings(self, t):
        if not isfinite(t) or not 0 <= t <= self.duration:
            raise ValueError('Time outside pulse')
        u = t / self.duration
        # Couple receiver B-to-bus first, sender A-to-bus second.
        gb = self.peak * exp(-0.5*((u-self.center_early)/self.sigma)**2)
        ga = self.peak * exp(-0.5*((u-self.center_late)/self.sigma)**2)
        return ga, gb


def _static_liouvillian(kappa, gamma_measure_a=0, gamma_phonon=0):
    # Dissipator only. Lindblad rates defined from L = sqrt(rate) |j><j|.
    m = Model(g_a=0, g_b=0, kappa=kappa, gamma_a=gamma_measure_a,
              gamma_phonon=gamma_phonon)
    return liouvillian(m)


def pulse_trajectory(pulse: Pulse, kappa=0, gamma_measure_a=0,
                     gamma_phonon=0, detuning_phonon=0, detuning_b=0,
                     steps=161, rtol=3e-10, atol=3e-12):
    """Evaluate a completely positive time-local Lindblad evolution numerically.

    This integrator uses DOP853 with mesh sampling. Finite numerical tolerances
    do not guarantee exact positivity: validate eigenvalues in each output.
    """
    for name, value in [('kappa', kappa), ('gamma_measure_a', gamma_measure_a),
                        ('gamma_phonon', gamma_phonon)]:
        if not isfinite(value) or value < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    for name, val in [('detuning_phonon', detuning_phonon),
                      ('detuning_b', detuning_b)]:
        if not isfinite(val):
            raise ValueError(f'{name} must be finite')
    if steps < 3 or not isinstance(steps, int):
        raise ValueError('steps must be integer at least three')
    if rtol <= 0 or atol <= 0 or not isfinite(rtol) or not isfinite(atol):
        raise ValueError('rtol and atol must be finite and positive')

    # Fixed dissipator; time-varying unitary component from the pulses.
    diss = _static_liouvillian(kappa, gamma_measure_a, gamma_phonon)
    rho0 = np.zeros((4, 4), complex)
    rho0[0, 0] = 1
    t_eval = np.linspace(0, pulse.duration, steps)
    eye = np.eye(4)
    def rhs(t, y):
        ga, gb = pulse.couplings(t)
        h = np.diag([0, detuning_phonon, detuning_b, 0]).astype(complex)
        h[0, 1] = h[1, 0] = ga
        h[1, 2] = h[2, 1] = gb
        unitary = -1j*(np.kron(eye,h)-np.kron(h.T,eye))
        return (unitary+diss)@y

    sol = solve_ivp(rhs, (0, pulse.duration), rho0.reshape(-1, order='F'),
                    method='DOP853', t_eval=t_eval, rtol=rtol, atol=atol)
    if not sol.success:
        raise RuntimeError(f'Pulse integration failed: {sol.message}')
    matrices = [y.reshape((4,4),order='F') for y in sol.y.T]
    population = np.array([np.real(np.diag(rho)) for rho in matrices])
    eigenmins = [float(np.linalg.eigvalsh((rho+rho.conj().T)/2).min())
                 for rho in matrices]
    traces = [float(np.trace(rho).real) for rho in matrices]
    phonon_integral = float(trapezoid(population[:,1],t_eval))
    final = metrics(matrices[-1])
    return {
        'final': final,
        'max_phonon_population': float(population[:,1].max()),
        'integrated_phonon_population': phonon_integral,
        'loss_integral_estimate': float(kappa * phonon_integral),
        'max_trace_error': float(np.max(np.abs(np.array(traces)-1))),
        'minimum_sampled_eigenvalue': float(min(eigenmins)),
        'time': t_eval.tolist(),
        'population_a': population[:,0].tolist(),
        'population_phonon': population[:,1].tolist(),
        'population_b': population[:,2].tolist(),
        'population_loss': population[:,3].tolist(),
    }


def constant_trajectory(duration, kappa=0, gamma_measure_a=0, steps=161):
    """Symmetric static-bus comparison at *identical elapsed duration*.

    The maximum-B value across [0, duration] is also returned, preventing
    a misleading comparison that ignores earlier optima of the static bus.
    """
    if not isfinite(duration) or duration <= 0 or not isinstance(steps, int) or steps < 3:
        raise ValueError('Invalid duration or steps')
    m = Model(kappa=kappa, gamma_a=gamma_measure_a)
    times = np.linspace(0,duration,steps)
    samples = np.array([[metrics(density_at(m,float(t)))[name]
                         for name in ('qubit_a','phonon','qubit_b','environment_loss')]
                        for t in times])
    # Static Liouvillian exactly exponentiated; here speed is secondary to auditable comparison.
    return {
        'final': dict(zip(('qubit_a','phonon','qubit_b','environment_loss'),map(float,samples[-1]))),
        'max_b_anytime': float(samples[:,2].max()),
        'time_of_max_b': float(times[samples[:,2].argmax()]),
        'max_phonon_population': float(samples[:,1].max()),
        'integrated_phonon_population': float(trapezoid(samples[:,1],times)),
    }


def site_monitoring_at(gamma, duration):
    """Nonselective monitoring of sender site |A> via Lindblad projector.

    Measurement induced dephasing is mathematically distinct from irreversible
    leakage of the shared phonon mode, modeled by kappa.
    """
    m = Model(gamma_a=gamma)
    return metrics(density_at(m,duration))

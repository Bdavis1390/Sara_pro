"""Independent physics invariants, analytic limits, and numerical cross-checks."""
import unittest
import numpy as np
from scipy.integrate import solve_ivp
from ws_qphonon_zeno.model import (
    Model, attenuated_coupling, density_at, hamiltonian, ideal_swap_time,
    liouvillian, metrics,
)


class PhysicsTests(unittest.TestCase):
    def test_ideal_full_swap(self):
        p = metrics(density_at(Model(), ideal_swap_time()))
        self.assertAlmostEqual(p['qubit_b'], 1.0, places=10)
        self.assertAlmostEqual(p['qubit_a'] + p['phonon'] + p['environment_loss'], 0, places=10)

    def test_analytic_time_curve(self):
        # Exact |A> -> |B> probability for a symmetric, lossless three-site chain.
        for t in (0, 0.2, 0.8, 1.5, ideal_swap_time()):
            got = metrics(density_at(Model(), t))['qubit_b']
            expected = ((1 - np.cos(np.sqrt(2) * t)) / 2) ** 2
            self.assertAlmostEqual(got, expected, places=11)

    def test_uncoupled_receiver(self):
        for t in (0, 0.5, 10):
            self.assertAlmostEqual(metrics(density_at(Model(g_b=0), t))['qubit_b'], 0, places=11)

    def test_open_system_valid_density(self):
        m = Model(g_b=0.5, kappa=0.7, gamma_a=0.2, gamma_b=0.4, gamma_phonon=0.9, detuning_phonon=1)
        for t in (0, 0.1, 0.8, 5, 20):
            rho = density_at(m, t)
            self.assertLess(np.max(np.abs(rho - rho.conj().T)), 1e-10)
            self.assertAlmostEqual(np.trace(rho).real, 1, places=10)
            self.assertGreaterEqual(np.min(np.linalg.eigvalsh(rho)), -1e-10)

    def test_loss_sink_is_monotone(self):
        m = Model(kappa=2)
        values = [metrics(density_at(m, t))['environment_loss'] for t in np.linspace(0, 6, 13)]
        self.assertTrue(all(b >= a - 1e-11 for a, b in zip(values, values[1:])))

    def test_strong_phonon_loss_inhibits_transfer(self):
        t = ideal_swap_time()
        ideal = metrics(density_at(Model(), t))
        strong = metrics(density_at(Model(kappa=100), t))
        self.assertGreater(ideal['qubit_b'], 0.999)
        self.assertGreater(strong['qubit_a'], 0.90)
        self.assertLess(strong['qubit_b'], 0.01)

    def test_strong_dephasing_inhibits_transfer(self):
        t = ideal_swap_time()
        strong = metrics(density_at(Model(gamma_a=100, gamma_b=100, gamma_phonon=100), t))
        self.assertGreater(strong['qubit_a'], 0.90)
        self.assertLess(strong['qubit_b'], 0.01)
        self.assertAlmostEqual(strong['environment_loss'], 0, places=11)

    def test_hamiltonian_hermitian_and_liouvillian_vs_ode(self):
        m = Model(g_a=0.9, g_b=0.7, detuning_a=0.25, detuning_phonon=-1.2,
                  phase=0.75, kappa=0.4, gamma_a=0.2, gamma_b=0.3)
        self.assertLess(np.max(abs(hamiltonian(m) - hamiltonian(m).conj().T)), 1e-14)
        rho0 = np.zeros((4, 4), complex); rho0[0, 0] = 1
        vec = rho0.reshape(16, order='F')
        gen = liouvillian(m)
        ode = solve_ivp(lambda t, y: gen @ y, [0, 1.3], vec, rtol=1e-11, atol=1e-12)
        direct = density_at(m, 1.3).reshape(16, order='F')
        self.assertTrue(ode.success)
        self.assertLess(np.max(abs(direct - ode.y[:, -1])), 2e-10)

    def test_phase_is_gauge_only_on_open_chain(self):
        t = ideal_swap_time()
        plain = metrics(density_at(Model(), t))
        phased = metrics(density_at(Model(phase=1.337), t))
        for name in ('qubit_a', 'phonon', 'qubit_b', 'environment_loss'):
            self.assertAlmostEqual(plain[name], phased[name], places=11)

    def test_detuning_reduces_nominal_swap(self):
        t = ideal_swap_time()
        self.assertLess(metrics(density_at(Model(detuning_phonon=12), t))['qubit_b'], 0.2)

    def test_attenuation_contract(self):
        self.assertAlmostEqual(attenuated_coupling(1, 0), 1)
        self.assertAlmostEqual(attenuated_coupling(1, 2), np.exp(-1))

    def test_reject_invalid_parameters(self):
        with self.assertRaises(ValueError): Model(kappa=-1)
        with self.assertRaises(ValueError): Model(phase=float('nan'))
        with self.assertRaises(ValueError): density_at(Model(), -1)
        with self.assertRaises(ValueError): attenuated_coupling(1, -1)


if __name__ == '__main__':
    unittest.main()

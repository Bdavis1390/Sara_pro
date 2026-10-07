import math
import unittest
import numpy as np
from ws_qphonon_multimode.model import (
    Mode, MultiModeModel, bose_occupation, propagation_delay_s,
    propagation_phase_rad, hamiltonian, initial_qubit_density,
    evolve, receiver_reduced, six_state_average_fidelity,
    best_phase_corrected_fidelity, state_metrics, paper_parameter_context,
)


def one_mode(q=1e30, temperature=0.0, phase=0.0):
    return MultiModeModel((Mode(25e9, 0, 1e6, 1e6, q, phase),), temperature_k=temperature)


class ThermalTests(unittest.TestCase):
    def test_zero_temperature_zero_occupation(self):
        self.assertEqual(bose_occupation(10e9, 0), 0.0)

    def test_occupation_decreases_with_frequency(self):
        self.assertGreater(bose_occupation(10e9, .1), bose_occupation(50e9, .1))

    def test_occupation_increases_with_temperature(self):
        self.assertGreater(bose_occupation(25e9, .1), bose_occupation(25e9, .05))

    def test_high_thermal_rejected_by_default(self):
        mode = Mode(10e9, 0, 1e6, 1e6, 1e5)
        with self.assertRaisesRegex(ValueError, "single-excitation limit"):
            MultiModeModel((mode,), temperature_k=1.0)


class PropagationTests(unittest.TestCase):
    def test_delay(self):
        self.assertAlmostEqual(propagation_delay_s(100e-6, 4000), 25e-9)

    def test_phase_is_wrapped(self):
        p = propagation_phase_rad(25e9, 100e-6, 4000)
        self.assertGreaterEqual(p, 0)
        self.assertLess(p, 2*math.pi)


class DynamicsTests(unittest.TestCase):
    def test_hamiltonian_is_hermitian(self):
        h = hamiltonian(one_mode())
        self.assertLess(np.max(np.abs(h-h.conj().T)), 1e-12)

    def test_liouvillian_trace_preserving(self):
        m = one_mode(q=1e5)
        rho = initial_qubit_density(m, 0, 1)
        out = evolve(m, rho, 2e-7)
        sm = state_metrics(out)
        self.assertLess(sm['trace_error'], 1e-10)
        self.assertGreater(sm['minimum_eigenvalue'], -1e-10)

    def test_receiver_reduced_trace(self):
        m = one_mode()
        rho = evolve(m, initial_qubit_density(m, 1/np.sqrt(2), 1/np.sqrt(2)), 1e-7)
        r = receiver_reduced(m, rho)
        self.assertAlmostEqual(np.trace(r).real, 1.0, places=12)
        self.assertGreaterEqual(np.min(np.linalg.eigvalsh(r)), -1e-10)

    def test_ideal_one_mode_phase_corrected_transfer(self):
        m = one_mode()
        t = 1/(2*np.sqrt(2)*1e6)
        r = best_phase_corrected_fidelity(m, t, phase_points=361)
        self.assertGreater(r['phase_corrected_six_state_fidelity'], 0.999999)

    def test_loss_reduces_transfer_fidelity(self):
        t = 1/(2*np.sqrt(2)*1e6)
        ideal = best_phase_corrected_fidelity(one_mode(), t)['phase_corrected_six_state_fidelity']
        lossy = best_phase_corrected_fidelity(one_mode(q=1e4), t)['phase_corrected_six_state_fidelity']
        self.assertLess(lossy, ideal)

    def test_phase_correction_never_worse(self):
        m = one_mode(phase=1.2)
        t = 1/(2*np.sqrt(2)*1e6)
        r = best_phase_corrected_fidelity(m, t)
        self.assertGreaterEqual(r['phase_corrected_six_state_fidelity']+1e-12, r['raw_six_state_fidelity'])

    def test_zero_time_channel_not_transfer(self):
        m = one_mode()
        f = six_state_average_fidelity(m, 0)
        self.assertLess(f, 0.7)

    def test_multimode_validity(self):
        modes = (
            Mode(25e9, -4e6, .3e6, .25e6, 1e5, .1),
            Mode(25e9, 0, 1e6, 1e6, 1e5, .2),
            Mode(25e9, 6e6, .25e6, .35e6, 1e5, -.3),
        )
        m = MultiModeModel(modes, temperature_k=.05)
        out = evolve(m, initial_qubit_density(m, 0, 1), 3e-7)
        sm = state_metrics(out)
        self.assertLess(sm['trace_error'], 2e-9)
        self.assertGreater(sm['minimum_eigenvalue'], -2e-9)


class ProvenanceTests(unittest.TestCase):
    def test_paper_context_is_bounded(self):
        c = paper_parameter_context()
        self.assertEqual(c['source_doi'], '10.1063/5.0332643')
        self.assertEqual(c['phonon_frequency_ghz_range'], [10.0, 50.0])
        self.assertIn('NOT WORLD SHEPHERD LAB DATA', c['classification'])

    def test_reject_bad_parameters(self):
        with self.assertRaises(ValueError): Mode(-1, 0, 1, 1, 1)
        with self.assertRaises(ValueError): propagation_delay_s(1, 0)
        with self.assertRaises(ValueError): bose_occupation(0, .1)


if __name__ == '__main__':
    unittest.main()

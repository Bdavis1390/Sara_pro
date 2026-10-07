"""Bona fide checks on pulse transport and measurement-induced suppression."""
import unittest
from ws_qphonon_zeno.model import Model, density_at, ideal_swap_time, metrics
from ws_qphonon_zeno.coherent import (Pulse, constant_trajectory,
                                        pulse_trajectory, site_monitoring_at)


class PulseTests(unittest.TestCase):
    def test_pulse_counterintuitive(self):
        p = Pulse()
        a0,b0 = p.couplings(0)
        a1,b1 = p.couplings(p.duration)
        self.assertGreater(b0, a0)
        self.assertGreater(a1, b1)
        for ga,gb in [p.couplings(i*p.duration/10) for i in range(11)]:
            self.assertLessEqual(max(ga,gb),p.peak*(1+1e-12))

    def test_zero_peak_stays_at_a(self):
        p = Pulse(peak=0,duration=4)
        row = pulse_trajectory(p, kappa=10)
        self.assertAlmostEqual(row['final']['qubit_a'],1,places=10)
        self.assertAlmostEqual(row['final']['qubit_b'],0,places=10)

    def test_positive_trace_loss(self):
        row = pulse_trajectory(Pulse(duration=12), kappa=.4)
        self.assertLess(row['max_trace_error'],1e-9)
        self.assertGreater(row['minimum_sampled_eigenvalue'],-1e-9)
        self.assertGreaterEqual(row['final']['environment_loss'],-1e-9)
        self.assertLessEqual(row['final']['environment_loss'],1+1e-9)
        self.assertTrue(all(b+1e-9>=a for a,b in zip(row['population_loss'],row['population_loss'][1:])))

    def test_loss_integral_conservation(self):
        r = pulse_trajectory(Pulse(duration=15),kappa=.6,steps=401)
        # dP_loss/dt = kappa * P_phonon for one absorbing Lindblad jump.
        self.assertAlmostEqual(r['loss_integral_estimate'],r['final']['environment_loss'],delta=0.0001)

    def test_no_loss_when_monitoring_only(self):
        row = pulse_trajectory(Pulse(duration=5),gamma_measure_a=5)
        self.assertAlmostEqual(row['final']['environment_loss'],0,places=10)

    def test_monitoring_inhibits_transfer(self):
        t=ideal_swap_time()
        base=site_monitoring_at(0,t)
        big=site_monitoring_at(100,t)
        self.assertGreater(base['qubit_b'],.9999)
        self.assertLess(big['qubit_b'],.06)
        self.assertAlmostEqual(big['environment_loss'],0,places=10)
        self.assertGreater(big['qubit_a'],.85)

    def test_continuous_limit_matches_static_unitary(self):
        # With constant coupling and no dissipator, the analytic solution
        # already has a separate reference test in the baseline suite.
        t=ideal_swap_time()
        exact=metrics(density_at(Model(),t))
        approx=constant_trajectory(t,steps=61)['final']
        self.assertAlmostEqual(exact['qubit_b'],approx['qubit_b'],places=11)

    def test_solver_tolerance_convergence(self):
        p=Pulse(duration=12)
        coarse=pulse_trajectory(p,kappa=.4,rtol=1e-8,atol=1e-10)
        fine=pulse_trajectory(p,kappa=.4,rtol=1e-11,atol=1e-13)
        self.assertLess(abs(coarse['final']['qubit_b']-fine['final']['qubit_b']),5e-7)

    def test_increased_dephasing_no_postselection(self):
        for gamma in (0,0.1,1,30):
            row=site_monitoring_at(gamma,ideal_swap_time())
            self.assertAlmostEqual(sum(row[k] for k in ['qubit_a','phonon','qubit_b','environment_loss']),1,places=9)
            self.assertGreaterEqual(row['min_eigenvalue'],-1e-10)

    def test_detuning_perturbation(self):
        p=Pulse(duration=24)
        base=pulse_trajectory(p, kappa=.5)['final']['qubit_b']
        perturbed=pulse_trajectory(p, kappa=.5, detuning_b=2)['final']['qubit_b']
        self.assertLess(perturbed,base)

    def test_bad_params_fail(self):
        with self.assertRaises(ValueError): Pulse(duration=0)
        with self.assertRaises(ValueError): Pulse(center_late=.2)
        with self.assertRaises(ValueError): pulse_trajectory(Pulse(),kappa=-1)
        with self.assertRaises(ValueError): pulse_trajectory(Pulse(),steps=1)
        with self.assertRaises(ValueError): constant_trajectory(0)
        with self.assertRaises(ValueError): pulse_trajectory(Pulse(),detuning_b=float('nan'))


if __name__=='__main__': unittest.main()

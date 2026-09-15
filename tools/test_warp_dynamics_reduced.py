#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import sys

MODULE = Path(__file__).with_name("warp_dynamics_reduced.py")
spec = importlib.util.spec_from_file_location("warp_dynamics_reduced", MODULE)
wd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = wd
spec.loader.exec_module(wd)

class WarpDynamicsTests(unittest.TestCase):
    def test_pressureless_sigma8_benchmark(self):
        x = np.linspace(-4.0, 4.0, 20001)
        u = wd.shape_profile(x, sigma_R=8.0, vs=1.0)
        tc = wd.caustic_time_pressureless(x, u)
        self.assertAlmostEqual(tc, 0.25, delta=0.002)

    def test_compactness_bound(self):
        self.assertAlmostEqual(wd.passive_compactness_bound(0.5), 0.625)

    def test_gamma_above_two_rejected(self):
        with self.assertRaises(ValueError):
            wd.run_srhd(3.0, 0.15, nx=100)

    def test_short_srhd_state_is_physical(self):
        r = wd.run_srhd(2.0, 0.18, nx=180, horizon_baseline_tc=0.25)
        self.assertGreater(r.min_density, 0.0)
        self.assertGreater(r.min_pressure, 0.0)
        self.assertLess(r.max_sound_speed, 1.0)

if __name__ == "__main__":
    unittest.main()

import math
import unittest

import numpy as np

from research.ws_qbench_mgraph_v01.magnetic_graph import (
    apply_local_gauge,
    displacement_matrix,
    floquet_rabi_adjacency,
    generalized_laguerre,
    lambda1_metric,
    normalized_magnetic_laplacian,
    sample_loop_statistics,
)


class MagneticGraphTests(unittest.TestCase):
    def test_generalized_laguerre_known_values(self):
        self.assertAlmostEqual(generalized_laguerre(0, 3, 2.0), 1.0)
        self.assertAlmostEqual(generalized_laguerre(1, 2, 0.5), 2.5)
        self.assertAlmostEqual(generalized_laguerre(2, 0, 0.5), 0.125)

    def test_displacement_blocks_satisfy_adjoint_relation(self):
        plus = displacement_matrix(nmax=16, eta=0.7, sign=+1)
        minus = displacement_matrix(nmax=16, eta=0.7, sign=-1)
        self.assertLess(np.max(np.abs(plus - minus.conj().T)), 1e-12)

    def test_weak_coupling_limit_approaches_identity(self):
        d = displacement_matrix(nmax=8, eta=1e-8, sign=+1)
        self.assertLess(np.max(np.abs(d - np.eye(9))), 2e-7)

    def test_magnetic_laplacian_is_hermitian_and_bounded(self):
        a = floquet_rabi_adjacency(nmax=24, eta=0.8)
        lap = normalized_magnetic_laplacian(a)
        self.assertLess(np.max(np.abs(lap - lap.conj().T)), 1e-12)
        eig = np.linalg.eigvalsh(lap)
        self.assertGreaterEqual(float(eig[0]), -1e-12)
        self.assertLessEqual(float(eig[-1]), 2.0 + 1e-12)

    def test_local_gauge_preserves_laplacian_spectrum(self):
        a = floquet_rabi_adjacency(nmax=18, eta=0.6)
        phases = np.linspace(-math.pi, math.pi, a.shape[0], endpoint=False)
        b = apply_local_gauge(a, phases)
        e1 = np.linalg.eigvalsh(normalized_magnetic_laplacian(a))
        e2 = np.linalg.eigvalsh(normalized_magnetic_laplacian(b))
        self.assertLess(np.max(np.abs(e1 - e2)), 1e-11)

    def test_lambda1_rises_from_weak_to_ultrastrong_sample(self):
        weak = lambda1_metric(nmax=32, eta=0.02)
        usc = lambda1_metric(nmax=32, eta=0.50)
        self.assertGreater(usc, weak + 0.25)

    def test_loop_statistics_are_deterministic(self):
        a = sample_loop_statistics(
            nmax=20, eta=0.8, q=2, samples=250,
            rel_edge_threshold=1e-3, seed=123,
        )
        b = sample_loop_statistics(
            nmax=20, eta=0.8, q=2, samples=250,
            rel_edge_threshold=1e-3, seed=123,
        )
        self.assertEqual(a, b)
        self.assertGreaterEqual(a.frustrated_fraction, 0.0)
        self.assertLessEqual(a.frustrated_fraction, 1.0)


if __name__ == "__main__":
    unittest.main()

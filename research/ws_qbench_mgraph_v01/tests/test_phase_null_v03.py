import unittest

import numpy as np

from research.ws_qbench_mgraph_v01.phase_null_v03 import (
    delta_signs,
    lambda1_from_hopping,
    permute_delta_sign_topology,
)


class PhaseNullV03Tests(unittest.TestCase):
    def setUp(self):
        self.k = np.array(
            [
                [1.0, 1.0j, -1.0, -1.0j],
                [1.0j, -2.0, -2.0j, 2.0],
                [-1.0, -2.0j, 3.0, 3.0j],
                [-1.0j, 2.0, 3.0j, -4.0],
            ],
            dtype=complex,
        )

    def test_lambda1_from_hopping_is_bounded(self):
        value = lambda1_from_hopping(self.k)
        self.assertGreaterEqual(value, -1e-12)
        self.assertLessEqual(value, 1.0 + 1e-12)

    def test_permutation_preserves_magnitudes_symmetry_and_band_sign_counts(self):
        rng = np.random.default_rng(123)
        null = permute_delta_sign_topology(self.k, rng)
        self.assertLess(np.max(np.abs(np.abs(null) - np.abs(self.k))), 1e-12)
        self.assertLess(np.max(np.abs(null - null.T)), 1e-12)
        for delta in range(self.k.shape[0]):
            self.assertEqual(
                sorted(delta_signs(self.k, delta)),
                sorted(delta_signs(null, delta)),
            )

    def test_permutation_is_seed_deterministic(self):
        a = permute_delta_sign_topology(self.k, np.random.default_rng(9675))
        b = permute_delta_sign_topology(self.k, np.random.default_rng(9675))
        self.assertTrue(np.array_equal(a, b))

    def test_rejects_phase_incompatible_input(self):
        bad = self.k.copy()
        bad[0, 1] = np.exp(0.3j)
        bad[1, 0] = bad[0, 1]
        with self.assertRaises(ValueError):
            permute_delta_sign_topology(bad, np.random.default_rng(1))


if __name__ == "__main__":
    unittest.main()

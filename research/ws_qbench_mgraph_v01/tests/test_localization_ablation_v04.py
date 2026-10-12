import unittest

import numpy as np

from research.ws_qbench_mgraph_v01.localization_ablation_v04 import (
    inverse_participation_ratios,
    phase_stripped_hopping,
    physical_hamiltonian_from_hopping,
    randomized_phase_hopping,
)


class LocalizationAblationV04Tests(unittest.TestCase):
    def test_physical_hamiltonian_is_hermitian(self):
        k = np.array([[1.0, 1.0j], [1.0j, -1.0]], dtype=complex)
        h = physical_hamiltonian_from_hopping(
            k, omega0=1.0, h_perp=0.5, h_parallel=0.1, h0=0.2
        )
        self.assertEqual(h.shape, (4, 4))
        self.assertLess(np.max(np.abs(h - h.conj().T)), 1e-12)

    def test_decoupled_spectrum_matches_two_stark_ladders(self):
        k = np.eye(3, dtype=complex)
        h = physical_hamiltonian_from_hopping(
            k, omega0=2.0, h_perp=0.0, h_parallel=0.25, h0=1.0
        )
        expected = np.sort(
            np.concatenate(
                [np.arange(3) * 2.0 + 1.0 + 0.25, np.arange(3) * 2.0 + 1.0 - 0.25]
            )
        )
        self.assertTrue(np.allclose(np.linalg.eigvalsh(h), expected))

    def test_ipr_known_basis_and_uniform_states(self):
        basis = np.eye(4, dtype=complex)
        self.assertTrue(np.allclose(inverse_participation_ratios(basis), 1.0))
        uniform = np.ones((4, 1), dtype=complex) / 2.0
        self.assertAlmostEqual(float(inverse_participation_ratios(uniform)[0]), 0.25)

    def test_phase_stripped_preserves_magnitude(self):
        k = np.array([[1j, -2.0], [3.0j, -4.0j]], dtype=complex)
        stripped = phase_stripped_hopping(k)
        self.assertTrue(np.array_equal(stripped, np.abs(k)))

    def test_random_phase_preserves_magnitude_and_seed(self):
        k = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=complex)
        a = randomized_phase_hopping(k, np.random.default_rng(123))
        b = randomized_phase_hopping(k, np.random.default_rng(123))
        self.assertTrue(np.allclose(np.abs(a), np.abs(k)))
        self.assertTrue(np.array_equal(a, b))

    def test_invalid_scale_rejected(self):
        with self.assertRaises(ValueError):
            physical_hamiltonian_from_hopping(
                np.eye(2), omega0=0.0, h_perp=1.0
            )
        with self.assertRaises(ValueError):
            physical_hamiltonian_from_hopping(
                np.eye(2), omega0=1.0, h_perp=-1.0
            )


if __name__ == "__main__":
    unittest.main()

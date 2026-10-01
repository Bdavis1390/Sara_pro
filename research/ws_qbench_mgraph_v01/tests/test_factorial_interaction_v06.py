import unittest

import numpy as np

from research.ws_qbench_mgraph_v01.factorial_interaction_v06 import (
    difference_in_differences,
    factorial_interaction_ablation,
)


class TestFactorialInteractionV06(unittest.TestCase):
    def test_difference_in_differences_zero_for_additive_shift(self):
        self.assertAlmostEqual(
            difference_in_differences(0.20, 0.35, 0.10, 0.25),
            0.0,
            places=15,
        )

    def test_difference_in_differences_detects_interaction(self):
        # Topology effect changes from 0.10 at reference to 0.15 at target.
        self.assertAlmostEqual(
            difference_in_differences(0.20, 0.50, 0.10, 0.35),
            0.05,
            places=15,
        )

    def test_tiny_physical_smoke_run_is_finite_and_deterministic(self):
        kwargs = dict(
            nmax=3,
            eta=0.4,
            reference_ratio=0.5,
            target_ratio=1.0,
            eigenstates=4,
            repetitions=3,
            seed=9675,
        )
        first = factorial_interaction_ablation(**kwargs)
        second = factorial_interaction_ablation(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(
            set(first),
            {"phase_stripped", "delta_sign_permuted", "randomized_phase"},
        )
        for row in first.values():
            for key in (
                "source_ref_mean_ipr",
                "source_target_mean_ipr",
                "null_ref_mean_ipr",
                "null_target_mean_ipr",
                "interaction_mean",
                "interaction_std",
            ):
                self.assertTrue(np.isfinite(float(row[key])))

    def test_reference_equals_target_forces_zero_interaction(self):
        result = factorial_interaction_ablation(
            nmax=3,
            eta=0.4,
            reference_ratio=1.0,
            target_ratio=1.0,
            eigenstates=4,
            repetitions=3,
            seed=9675,
        )
        for row in result.values():
            self.assertAlmostEqual(float(row["interaction_mean"]), 0.0, places=12)
            self.assertAlmostEqual(float(row["interaction_std"]), 0.0, places=12)

    def test_negative_scale_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            factorial_interaction_ablation(
                nmax=3,
                eta=0.4,
                reference_ratio=-0.1,
                target_ratio=1.0,
            )


if __name__ == "__main__":
    unittest.main()

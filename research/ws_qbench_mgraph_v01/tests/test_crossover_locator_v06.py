import unittest

from research.ws_qbench_mgraph_v01.crossover_locator_v06 import (
    bracket_zero_crossing,
    cutoff_consensus,
    estimate_all_crossovers,
    estimate_crossover,
)


class TestCrossoverLocatorV06(unittest.TestCase):
    def test_bracket_detects_sign_change(self):
        bracket = bracket_zero_crossing([(2.0, -0.1), (3.0, 0.1)])
        self.assertEqual(bracket, ((2.0, -0.1), (3.0, 0.1)))

    def test_no_sign_change_returns_none(self):
        self.assertIsNone(estimate_crossover([(1.0, -0.2), (2.0, -0.1)]))

    def test_linear_interpolation(self):
        row = estimate_crossover([(1.0, -0.25), (2.0, 0.75)])
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row.estimated_ratio, 1.25, places=15)

    def test_exact_zero_is_preserved(self):
        row = estimate_crossover([(1.0, -0.2), (1.5, 0.0), (2.0, 0.3)])
        self.assertIsNotNone(row)
        self.assertEqual(row.estimated_ratio, 1.5)

    def test_reentrant_curve_preserves_all_crossings(self):
        rows = estimate_all_crossovers(
            [(1.0, 0.2), (2.0, -0.2), (3.0, -0.1), (4.0, 0.3)]
        )
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0].estimated_ratio, 1.5, places=15)
        self.assertAlmostEqual(rows[1].estimated_ratio, 3.25, places=15)

    def test_duplicate_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_all_crossovers([(1.0, -0.2), (1.0, 0.2)])

    def test_cutoff_consensus_retains_spread(self):
        summary = cutoff_consensus([1.9, 2.0, 2.1])
        self.assertEqual(summary["count"], 3)
        self.assertAlmostEqual(summary["mean"], 2.0)
        self.assertAlmostEqual(summary["spread"], 0.2)

    def test_empty_consensus_rejected(self):
        with self.assertRaises(ValueError):
            cutoff_consensus([])


if __name__ == "__main__":
    unittest.main()

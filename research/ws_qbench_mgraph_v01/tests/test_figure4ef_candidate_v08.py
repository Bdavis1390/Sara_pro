import unittest

import numpy as np

from research.ws_qbench_mgraph_v01.figure4ef_candidate_v08 import (
    adjacent_gap_diagnostic,
    state_resolved_figure4ef,
)


class TestFigure4EFCandidateV08(unittest.TestCase):
    def test_state_resolved_smoke(self):
        row = state_resolved_figure4ef(0.5, nmax=6, eigenstates=6)
        self.assertEqual(row.nmax, 6)
        self.assertEqual(row.eigenstates, 6)
        self.assertEqual(len(row.energies), 6)
        self.assertEqual(len(row.ipr), 6)
        self.assertTrue(np.all(np.isfinite(row.energies)))
        self.assertTrue(np.all(np.isfinite(row.ipr)))
        self.assertTrue(np.all(np.diff(row.energies) >= -1e-12))

    def test_ipr_is_bounded(self):
        row = state_resolved_figure4ef(1.0, nmax=5, eigenstates=8)
        self.assertTrue(all(0.0 < value <= 1.0 for value in row.ipr))

    def test_gap_diagnostic_is_finite(self):
        row = adjacent_gap_diagnostic(1.0, nmax=5, eigenstates=8)
        self.assertGreaterEqual(row["min_adjacent_gap"], -1e-12)
        self.assertGreaterEqual(row["count_gap_lt_1e-3"], 0)

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            state_resolved_figure4ef(-0.1)
        with self.assertRaises(ValueError):
            state_resolved_figure4ef(0.5, nmax=0)
        with self.assertRaises(ValueError):
            state_resolved_figure4ef(0.5, eigenstates=0)


if __name__ == "__main__":
    unittest.main()

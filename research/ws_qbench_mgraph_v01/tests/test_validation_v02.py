import unittest
from unittest.mock import patch

import numpy as np

from research.ws_qbench_mgraph_v01.validation_v02 import (
    complete_bipartite_null_conductance,
    cutoff_convergence,
    sample_random_subgraphs,
    subgraph_conductance_from_hopping,
    weak_coupling_diagnostics,
)


class ValidationV02Tests(unittest.TestCase):
    def test_subgraph_conductance_known_case(self):
        k = np.ones((2, 2), dtype=complex)
        self.assertAlmostEqual(
            subgraph_conductance_from_hopping(k, [0], [0]), 0.5
        )
        self.assertAlmostEqual(
            subgraph_conductance_from_hopping(k, [0, 1], [0, 1]), 0.0
        )

    def test_complete_bipartite_null(self):
        self.assertAlmostEqual(
            complete_bipartite_null_conductance(200, 2), 1.0 - 2.0 / 201.0
        )
        self.assertAlmostEqual(
            complete_bipartite_null_conductance(200, 50), 1.0 - 50.0 / 201.0
        )

    def test_conductance_rejects_duplicate_nodes(self):
        k = np.ones((3, 3), dtype=complex)
        with self.assertRaises(ValueError):
            subgraph_conductance_from_hopping(k, [0, 0], [1, 2])

    @patch(
        "research.ws_qbench_mgraph_v01.validation_v02.floquet_rabi_hopping",
        return_value=np.ones((2, 2), dtype=complex),
    )
    def test_loop_probabilities_close_exactly(self, _mock_hopping):
        stats = sample_random_subgraphs(
            nmax=1,
            eta=0.5,
            q=2,
            samples=20,
            rel_edge_threshold=1e-3,
            seed=123,
        )
        self.assertEqual(stats.p_connect, 1.0)
        self.assertEqual(stats.p_nontrivial, 0.0)
        self.assertEqual(stats.p_trivial, 1.0)
        self.assertAlmostEqual(
            stats.p_nontrivial + stats.p_trivial, stats.p_connect
        )
        self.assertEqual(stats.max_phase_quantization_error, 0.0)
        self.assertEqual(stats.complete_bipartite_null, 0.0)
        self.assertEqual(stats.conductance_excess_over_null, 0.0)

    @patch("research.ws_qbench_mgraph_v01.validation_v02.lambda1_metric")
    def test_cutoff_convergence_uses_largest_reference(self, mock_lambda1):
        mock_lambda1.side_effect = lambda nmax, eta: eta + 1.0 / nmax
        rows = cutoff_convergence(eta=0.5, nmax_values=(10, 20, 40))
        self.assertEqual(rows[-1].absolute_error, 0.0)
        self.assertEqual(rows[-1].reference_nmax, 40)
        self.assertGreater(rows[0].absolute_error, rows[1].absolute_error)

    @patch("research.ws_qbench_mgraph_v01.validation_v02.lambda1_metric")
    def test_weak_coupling_diagnostics(self, mock_lambda1):
        mock_lambda1.side_effect = lambda nmax, eta: 1.99 * eta
        rows = weak_coupling_diagnostics(etas=(0.01, 0.02), nmax=20)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(rows[0].relative_error, 0.005)


if __name__ == "__main__":
    unittest.main()

import unittest

from research.ws_qbench_mgraph_v01.loop_zero_semantics_v09 import (
    classify_phase,
    loop_probability_audit,
    probability_identity_residual,
)


class TestLoopZeroSemanticsV09(unittest.TestCase):
    def test_exact_zero_is_disconnected(self):
        self.assertIsNone(classify_phase(0.0 + 0.0j))

    def test_zero_and_pi_classes(self):
        self.assertEqual(classify_phase(1.0 + 0.0j), "trivial")
        self.assertEqual(classify_phase(-1.0 + 0.0j), "nontrivial")

    def test_small_run_preserves_probability_identity(self):
        row = loop_probability_audit(
            eta=0.5,
            q=2,
            nmax=8,
            realizations=200,
            seed=9675,
        )
        self.assertEqual(row.unclassified_connected, 0)
        self.assertAlmostEqual(probability_identity_residual(row), 0.0, places=15)

    def test_deterministic_seed(self):
        kwargs = dict(
            eta=1.0,
            q=3,
            nmax=8,
            realizations=100,
            seed=9675,
        )
        self.assertEqual(
            loop_probability_audit(**kwargs),
            loop_probability_audit(**kwargs),
        )

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            loop_probability_audit(-0.1, 2)
        with self.assertRaises(ValueError):
            loop_probability_audit(0.5, 1)
        with self.assertRaises(ValueError):
            loop_probability_audit(0.5, 2, realizations=0)


if __name__ == "__main__":
    unittest.main()

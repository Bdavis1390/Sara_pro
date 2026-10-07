"""Fail-closed regression tests for protocol health gates."""
import copy
import unittest

from run_protocol import gate_check


def valid_run():
    return {
        'max_trace_error': 0.0,
        'minimum_sampled_eigenvalue': 0.0,
        'loss_integral_estimate': 0.0,
        'final': {
            'qubit_a': 1.0,
            'phonon': 0.0,
            'qubit_b': 0.0,
            'environment_loss': 0.0,
        },
    }


class HealthGateTests(unittest.TestCase):
    def test_rejects_nan_metric(self):
        run = copy.deepcopy(valid_run())
        run['max_trace_error'] = float('nan')
        with self.assertRaisesRegex(RuntimeError, 'non-finite'):
            gate_check(run)

    def test_rejects_infinite_probability(self):
        run = copy.deepcopy(valid_run())
        run['final']['qubit_b'] = float('inf')
        run['final']['qubit_a'] = float('-inf')
        with self.assertRaisesRegex(RuntimeError, 'non-finite'):
            gate_check(run)


if __name__ == '__main__':
    unittest.main()

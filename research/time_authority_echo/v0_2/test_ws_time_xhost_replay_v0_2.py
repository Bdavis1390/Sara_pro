import json
import unittest
from pathlib import Path

from worldshepherd_time_authority_v0_2 import ExternalCalibrationSample, TimeAuthority

FIXTURE = json.loads((Path(__file__).resolve().parent / 'ws_time_xhost_replay_fixture.json').read_text())


def replay_node(name):
    authority = TimeAuthority(external_max_uncertainty_s=FIXTURE['policy_max_uncertainty_s'])
    decisions = []
    for sequence, row in enumerate(FIXTURE['nodes'][name], start=1):
        uo, uu = row['utctime']
        to, tu = row['timeapi']
        decision = authority.evaluate_external_calibration([
            ExternalCalibrationSample('utctime.app', sequence, uo, uu),
            ExternalCalibrationSample('timeapi.io', sequence, to, tu),
        ])
        decisions.append((decision, row['expected']))
    return decisions


class HostedReplayTests(unittest.TestCase):
    def test_qcrypto_replays_7_consistent_1_degraded(self):
        results = replay_node('qcrypto')
        states = [d.state for d, _ in results]
        self.assertEqual(states.count('CONSISTENT'), 7)
        self.assertEqual(states.count('DEGRADED'), 1)
        self.assertEqual(states, [expected for _, expected in results])

    def test_recovery_replays_7_consistent_1_degraded(self):
        results = replay_node('recovery')
        states = [d.state for d, _ in results]
        self.assertEqual(states.count('CONSISTENT'), 7)
        self.assertEqual(states.count('DEGRADED'), 1)
        self.assertEqual(states, [expected for _, expected in results])

    def test_qcrypto_spike_fails_uncertainty_ceiling(self):
        d, _ = replay_node('qcrypto')[-1]
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('EXTERNAL_CALIBRATION_UNCERTAINTY_TOO_WIDE', d.reasons)
        self.assertGreater(d.uncertainty_s, FIXTURE['policy_max_uncertainty_s'])

    def test_recovery_spike_fails_uncertainty_ceiling(self):
        d, _ = replay_node('recovery')[-2]
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('EXTERNAL_CALIBRATION_UNCERTAINTY_TOO_WIDE', d.reasons)
        self.assertGreater(d.uncertainty_s, FIXTURE['policy_max_uncertainty_s'])

    def test_large_recovery_point_spread_can_still_be_consistent(self):
        d, _ = replay_node('recovery')[1]
        raw_spread = abs(0.1155 - 0.0125)
        self.assertGreater(raw_spread, 0.100)
        self.assertEqual(d.state, 'CONSISTENT')
        self.assertLessEqual(d.uncertainty_s, FIXTURE['policy_max_uncertainty_s'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

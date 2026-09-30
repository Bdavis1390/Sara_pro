import unittest
from worldshepherd_time_authority_v0_2 import (
    ClockSample,
    ExternalCalibrationSample,
    TimeAuthority,
)


def samples(t, seq, offsets=(0.0004, -0.0005, 0.0002), prov=(True, True, True)):
    return [ClockSample(f's{i}', seq, t + offsets[i], t, prov[i]) for i in range(3)]


def ext(provider, seq, offset, uncertainty, prov=True):
    return ExternalCalibrationSample(provider, seq, offset, uncertainty, prov)


class LegacyTimeAuthorityTests(unittest.TestCase):
    def test_nominal_promotes_after_hysteresis(self):
        a = TimeAuthority(clean_required=3)
        states = [a.evaluate(samples(q * .1, q), q * .1).state for q in range(4)]
        self.assertEqual(states[:2], ['DEGRADED', 'DEGRADED'])
        self.assertEqual(states[2:], ['TRUSTED', 'TRUSTED'])

    def test_common_mode_shift_is_not_trusted(self):
        a = TimeAuthority(clean_required=2)
        a.evaluate(samples(0, 0), 0)
        self.assertEqual(a.evaluate(samples(.1, 1), .1).state, 'TRUSTED')
        shifted = samples(.2, 2, offsets=(.0504, .0495, .0502))
        d = a.evaluate(shifted, .2)
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('HOLDOVER_PLAUSIBILITY_FAIL', d.reasons)

    def test_single_outlier_excluded_but_consensus_survives(self):
        a = TimeAuthority(clean_required=1)
        d = a.evaluate(samples(0, 0, offsets=(.0004, -.0005, .100)), 0)
        self.assertEqual(d.state, 'TRUSTED')
        self.assertEqual(len(d.agreeing_sources), 2)
        self.assertIn('SOURCE_OUTLIER_EXCLUDED', d.reasons)

    def test_two_disagreeing_sources_degrade(self):
        a = TimeAuthority(clean_required=1, min_sources=2, consensus_dispersion_s=.003)
        d = a.evaluate([ClockSample('a', 0, 0, 0), ClockSample('b', 0, .050, 0)], 0)
        self.assertEqual(d.state, 'DEGRADED')

    def test_insufficient_sources_unavailable(self):
        a = TimeAuthority(clean_required=1)
        d = a.evaluate([ClockSample('a', 0, 0, 0)], 0)
        self.assertEqual(d.state, 'UNAVAILABLE')

    def test_provenance_failure_excluded(self):
        a = TimeAuthority(clean_required=1)
        d = a.evaluate(samples(0, 0, prov=(True, True, False)), 0)
        self.assertEqual(d.state, 'TRUSTED')
        self.assertIn('PROVENANCE_REJECT:s2', d.reasons)

    def test_replay_rejected(self):
        a = TimeAuthority(clean_required=1)
        a.evaluate(samples(0, 1), 0)
        d = a.evaluate(samples(.1, 1), .1)
        self.assertEqual(d.state, 'UNAVAILABLE')
        self.assertTrue(any(r.startswith('REPLAY_REJECT') for r in d.reasons))

    def test_gradual_common_drift_eventually_demotes(self):
        a = TimeAuthority(clean_required=2, holdover_base_uncertainty_s=.002, holdover_drift_ppm=5)
        a.evaluate(samples(0, 0), 0)
        a.evaluate(samples(.1, 1), .1)
        state = None
        for q in range(2, 20):
            t = q * .1
            drift = .0005 * q
            state = a.evaluate(samples(t, q, offsets=(drift+.0004, drift-.0005, drift+.0002)), t).state
            if state == 'DEGRADED':
                break
        self.assertEqual(state, 'DEGRADED')

    def test_recovery_requires_clean_streak(self):
        a = TimeAuthority(clean_required=3)
        for q in range(3):
            a.evaluate(samples(q*.1, q), q*.1)
        d = a.evaluate(samples(.3, 3, offsets=(.0504, .0495, .0502)), .3)
        self.assertEqual(d.state, 'DEGRADED')
        r = [a.evaluate(samples(t, q), t).state for q, t in [(4,.4),(5,.5),(6,.6)]]
        self.assertEqual(r, ['DEGRADED', 'DEGRADED', 'TRUSTED'])

    def test_bound_expands_with_elapsed_holdover(self):
        a = TimeAuthority(clean_required=1, holdover_base_uncertainty_s=.001, holdover_drift_ppm=20)
        d0 = a.evaluate(samples(0, 0), 0)
        d1 = a.evaluate(samples(10, 1), 10)
        self.assertGreater(d1.holdover_bound_s, d0.holdover_bound_s)


class ExternalCalibrationTests(unittest.TestCase):
    def test_overlapping_heterogeneous_intervals_consistent(self):
        a = TimeAuthority(external_max_uncertainty_s=.025)
        # Mirrors the hosted shape: fast narrow path plus slow wide path.
        d = a.evaluate_external_calibration([
            ext('utctime.app', 1, .0015, .0075),
            ext('timeapi.io', 1, -.0010, .0590),
        ])
        self.assertEqual(d.state, 'CONSISTENT')
        self.assertAlmostEqual(d.offset_s, .0015, places=6)
        self.assertAlmostEqual(d.uncertainty_s, .0075, places=6)

    def test_point_spread_does_not_imply_disagreement_when_intervals_overlap(self):
        a = TimeAuthority(external_max_uncertainty_s=.025)
        d = a.evaluate_external_calibration([
            ext('fast', 1, .0125, .0185),
            ext('slow', 1, .1155, .1775),
        ])
        self.assertEqual(d.state, 'CONSISTENT')
        self.assertLessEqual(d.uncertainty_s, .025)

    def test_nonoverlap_degrades(self):
        a = TimeAuthority(external_max_uncertainty_s=.025)
        d = a.evaluate_external_calibration([
            ext('a', 1, 0.0, .002),
            ext('b', 1, .050, .002),
        ])
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('NO_EXTERNAL_INTERVAL_CONSENSUS', d.reasons)

    def test_wide_common_interval_degrades(self):
        a = TimeAuthority(external_max_uncertainty_s=.025)
        d = a.evaluate_external_calibration([
            ext('a', 1, 0.0, .080),
            ext('b', 1, .010, .080),
        ])
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('EXTERNAL_CALIBRATION_UNCERTAINTY_TOO_WIDE', d.reasons)

    def test_external_provenance_and_replay(self):
        a = TimeAuthority(min_external_providers=2)
        d = a.evaluate_external_calibration([
            ext('a', 1, 0.0, .005, False),
            ext('b', 1, 0.0, .005),
        ])
        self.assertEqual(d.state, 'UNAVAILABLE')
        self.assertIn('EXTERNAL_PROVENANCE_REJECT:a', d.reasons)
        a2 = TimeAuthority(min_external_providers=2)
        a2.evaluate_external_calibration([ext('a', 2, 0, .005), ext('b', 2, 0, .005)])
        d2 = a2.evaluate_external_calibration([ext('a', 2, 0, .005), ext('b', 2, 0, .005)])
        self.assertEqual(d2.state, 'UNAVAILABLE')
        self.assertTrue(any(x.startswith('EXTERNAL_REPLAY_REJECT') for x in d2.reasons))

    def test_external_anchor_required_blocks_internal_bootstrap(self):
        a = TimeAuthority(clean_required=1, require_external_anchor=True)
        d = a.evaluate(samples(0, 0), 0)
        self.assertEqual(d.state, 'DEGRADED')
        self.assertIn('EXTERNAL_ANCHOR_REQUIRED', d.reasons)

    def test_consistent_external_calibration_seeds_strict_anchor(self):
        a = TimeAuthority(clean_required=2, require_external_anchor=True)
        c = a.evaluate_external_calibration([
            ext('fast', 1, .002, .008),
            ext('slow', 1, .004, .060),
        ])
        ar = a.seed_external_anchor(c, local_wall_time=1000.0, local_monotonic=20.0)
        self.assertTrue(ar.accepted)
        self.assertEqual(a.evaluate(samples(1000.102, 1), 20.1).state, 'DEGRADED')
        d = a.evaluate(samples(1000.202, 2), 20.2)
        self.assertEqual(d.state, 'TRUSTED')
        self.assertEqual(d.anchor_source, 'EXTERNAL_INTERVAL_CALIBRATION')
        self.assertGreaterEqual(d.anchor_uncertainty_s, .008)

    def test_degraded_calibration_cannot_seed_anchor(self):
        a = TimeAuthority(require_external_anchor=True, external_max_uncertainty_s=.010)
        c = a.evaluate_external_calibration([
            ext('a', 1, 0, .050), ext('b', 1, 0, .050)
        ])
        self.assertEqual(c.state, 'DEGRADED')
        ar = a.seed_external_anchor(c, local_wall_time=100, local_monotonic=10)
        self.assertFalse(ar.accepted)

    def test_external_uncertainty_propagates_into_holdover_bound(self):
        a = TimeAuthority(clean_required=1, require_external_anchor=True,
                          holdover_base_uncertainty_s=.001, holdover_drift_ppm=20)
        c = a.evaluate_external_calibration([
            ext('a', 1, .001, .008), ext('b', 1, .002, .020)
        ])
        a.seed_external_anchor(c, local_wall_time=1000, local_monotonic=0)
        d0 = a.evaluate(samples(1000.1015, 1), .1)
        d1 = a.evaluate(samples(1010.0015, 2), 10.0)
        self.assertGreaterEqual(d0.holdover_bound_s, c.uncertainty_s)
        self.assertGreater(d1.holdover_bound_s, d0.holdover_bound_s)


if __name__ == '__main__':
    unittest.main(verbosity=2)

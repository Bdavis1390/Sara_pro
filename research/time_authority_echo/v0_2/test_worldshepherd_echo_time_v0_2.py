import copy
import hashlib
import unittest

from worldshepherd_time_authority_v0_2 import TimeDecision
from worldshepherd_echo_time_v0_2 import EchoTimeCustody


def td(
    state="TRUSTED",
    t=10.0,
    reasons=(),
    anchor_source="INTERNAL_SOURCE_CLUSTER",
    anchor_uncertainty=.007,
):
    return TimeDecision(
        state, t, 3, ('a', 'b', 'c'), .001, .0004, .007,
        tuple(reasons), anchor_source, anchor_uncertainty,
    )


PAYLOAD = hashlib.sha256(b'fixture').hexdigest()


class EchoTimeTests(unittest.TestCase):
    def test_trusted_time_authorized_default_policy(self):
        c = EchoTimeCustody()
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        self.assertTrue(r['time']['absolute_time_authorized'])
        self.assertEqual(r['ordering_mode'], 'ABSOLUTE_PLUS_MONOTONIC')
        self.assertEqual(r['time']['authoritative_time'], 10.0)
        self.assertTrue(c.verify_digest(r))

    def test_degraded_time_not_authoritative(self):
        c = EchoTimeCustody()
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD,
                    time_decision=td('DEGRADED', 10.0, ('HOLDOVER_PLAUSIBILITY_FAIL',)))
        self.assertFalse(r['time']['absolute_time_authorized'])
        self.assertIsNone(r['time']['authoritative_time'])
        self.assertEqual(r['ordering_mode'], 'MONOTONIC_ONLY')
        self.assertEqual(r['time']['observed_consensus_time'], 10.0)

    def test_monotonic_order_survives_unavailable_time(self):
        c = EchoTimeCustody()
        d = TimeDecision('UNAVAILABLE', None, 1, tuple(), None, None, None,
                         ('INSUFFICIENT_SOURCES',), None, None)
        r = c.issue(event_id='e1', event_counter=7, payload_digest=PAYLOAD, time_decision=d)
        self.assertEqual(r['event_counter'], 7)
        self.assertEqual(r['ordering_mode'], 'MONOTONIC_ONLY')

    def test_counter_replay_rejected(self):
        c = EchoTimeCustody()
        c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        with self.assertRaises(ValueError):
            c.issue(event_id='e2', event_counter=1, payload_digest=PAYLOAD, time_decision=td())

    def test_hash_chain_parent_binding(self):
        c = EchoTimeCustody()
        r1 = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        r2 = c.issue(event_id='e2', event_counter=2, payload_digest=PAYLOAD, time_decision=td(t=10.1))
        self.assertEqual(r2['parent_receipt_digest'], r1['receipt_digest'])
        self.assertTrue(c.verify_digest(r2))

    def test_mutation_breaks_digest(self):
        c = EchoTimeCustody()
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        m = copy.deepcopy(r)
        m['time']['anchor_uncertainty_s'] = .5
        self.assertFalse(c.verify_digest(m))

    def test_reason_preserved(self):
        c = EchoTimeCustody()
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD,
                    time_decision=td('DEGRADED', 10, ('CLOCK_DRIFT', 'SOURCE_OUTLIER_EXCLUDED')))
        self.assertEqual(r['time']['reasons'], ['CLOCK_DRIFT', 'SOURCE_OUTLIER_EXCLUDED'])

    def test_bad_payload_digest_rejected(self):
        c = EchoTimeCustody()
        with self.assertRaises(ValueError):
            c.issue(event_id='e1', event_counter=1, payload_digest='abc', time_decision=td())

    def test_anchor_source_and_uncertainty_are_retained(self):
        c = EchoTimeCustody()
        r = c.issue(
            event_id='e1', event_counter=1, payload_digest=PAYLOAD,
            time_decision=td(anchor_source='EXTERNAL_INTERVAL_CALIBRATION', anchor_uncertainty=.008),
        )
        self.assertEqual(r['time']['anchor_source'], 'EXTERNAL_INTERVAL_CALIBRATION')
        self.assertEqual(r['time']['anchor_uncertainty_s'], .008)

    def test_strict_echo_rejects_internal_anchor_for_absolute_time(self):
        c = EchoTimeCustody(require_external_anchor_for_absolute=True)
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        self.assertFalse(r['time']['absolute_time_authorized'])
        self.assertEqual(r['ordering_mode'], 'MONOTONIC_ONLY')
        self.assertIn('ECHO_EXTERNAL_ANCHOR_REQUIRED', r['time']['reasons'])

    def test_strict_echo_accepts_trusted_external_anchor(self):
        c = EchoTimeCustody(require_external_anchor_for_absolute=True)
        r = c.issue(
            event_id='e1', event_counter=1, payload_digest=PAYLOAD,
            time_decision=td(anchor_source='EXTERNAL_INTERVAL_CALIBRATION', anchor_uncertainty=.009),
        )
        self.assertTrue(r['time']['absolute_time_authorized'])
        self.assertTrue(r['time']['anchor_requirement_met'])

    def test_strict_echo_still_denies_degraded_external_anchor(self):
        c = EchoTimeCustody(require_external_anchor_for_absolute=True)
        r = c.issue(
            event_id='e1', event_counter=1, payload_digest=PAYLOAD,
            time_decision=td('DEGRADED', 10.0, ('RECOVERY_HYSTERESIS',),
                             anchor_source='EXTERNAL_INTERVAL_CALIBRATION', anchor_uncertainty=.009),
        )
        self.assertFalse(r['time']['absolute_time_authorized'])
        self.assertTrue(r['time']['anchor_requirement_met'])

    def test_schema_is_v02(self):
        c = EchoTimeCustody()
        r = c.issue(event_id='e1', event_counter=1, payload_digest=PAYLOAD, time_decision=td())
        self.assertEqual(r['schema'], 'WS-ECHO-TIME-RECEIPT-0.2')


if __name__ == '__main__':
    unittest.main(verbosity=2)

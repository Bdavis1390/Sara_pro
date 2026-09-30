import unittest
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.operational_events import SignificantOperationalEvent, evaluate_operational_event

UTC=timezone.utc
T=datetime(2026,9,18,21,0,tzinfo=UTC)


def event(**kw):
    data = dict(event_id="INC-1", reasonable_basis_at=T, event_time=T-timedelta(minutes=1), nature="service disruption", systems_impacted="matching/API", participant_impact="trading unavailable", participants_notified_at=T+timedelta(minutes=1), sec_notified_at=T+timedelta(minutes=2), remediation_completed_at=T+timedelta(minutes=20), remediation_notice_at=T+timedelta(minutes=21))
    data.update(kw)
    return SignificantOperationalEvent(**data)


class TestTsvOperationalEvents(unittest.TestCase):
    def test_complete_event_passes(self):
        self.assertEqual(evaluate_operational_event(event(), now=T+timedelta(hours=1))["decision"], "ALLOW")

    def test_missing_participant_notice_denies(self):
        self.assertIn("PARTICIPANT_NOTICE_MISSING", evaluate_operational_event(event(participants_notified_at=None), now=T)["errors"])

    def test_missing_sec_notice_denies(self):
        self.assertIn("SEC_NOTICE_MISSING", evaluate_operational_event(event(sec_notified_at=None), now=T)["errors"])

    def test_remediation_completion_requires_notice(self):
        self.assertIn("REMEDIATION_NOTICE_MISSING", evaluate_operational_event(event(remediation_notice_at=None), now=T+timedelta(hours=1))["errors"])

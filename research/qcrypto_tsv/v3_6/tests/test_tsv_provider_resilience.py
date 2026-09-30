import unittest
from datetime import date, datetime, time, timedelta, timezone
from worldshepherd_qcrypto_kms.tsv.provider_resilience import (
    ProviderHealth, ProviderRoute, CalendarEvidence, select_provider, validate_calendar_evidence,
)
UTC=timezone.utc
NOW=datetime(2026,9,19,2,0,tzinfo=UTC)
REG={'SIP':{'sip-a','sip-b'}}
ROUTE=ProviderRoute('SIP','sip-a',('sip-b',))

def h(pid,reachable=True,part='p1',age=1,verified=True):
    return ProviderHealth('SIP',pid,reachable,NOW-timedelta(seconds=age),part,verified)

def cal(provider='calendar-a',is_open=True,published=None,session=date(2026,9,19),verified=True):
    return CalendarEvidence(provider,'synthetic-market-calendar',session,is_open,time(13,30) if is_open else None,time(20,0) if is_open else None,published or NOW-timedelta(days=1),'a'*64,verified)

class TestProviderResilience(unittest.TestCase):
    def test_primary_selected_when_healthy(self):
        r=select_provider(ROUTE,[h('sip-a'),h('sip-b')],now=NOW,provider_registry=REG)
        self.assertEqual((r.decision,r.selected_provider_id,r.reason),('ALLOW','sip-a','PRIMARY_HEALTHY'))

    def test_fallback_selected_when_primary_down(self):
        r=select_provider(ROUTE,[h('sip-a',False),h('sip-b',True)],now=NOW,provider_registry=REG)
        self.assertEqual((r.decision,r.selected_provider_id),('ALLOW','sip-b'))
        self.assertEqual(r.reason,'FAILOVER_TO_REGISTERED_FALLBACK')

    def test_no_provider_denies(self):
        r=select_provider(ROUTE,[h('sip-a',False),h('sip-b',False)],now=NOW,provider_registry=REG)
        self.assertEqual(r.decision,'DENY'); self.assertIn('NO_REACHABLE_REGISTERED_PROVIDER',r.errors)

    def test_partition_disagreement_denies(self):
        r=select_provider(ROUTE,[h('sip-a',True,'p1'),h('sip-b',True,'p2')],now=NOW,provider_registry=REG)
        self.assertEqual(r.decision,'DENY'); self.assertIn('PROVIDER_PARTITION_DISAGREEMENT',r.errors)

    def test_stale_health_denies(self):
        r=select_provider(ROUTE,[h('sip-a',True,'p1',60),h('sip-b',False,'p1')],now=NOW,provider_registry=REG)
        self.assertEqual(r.decision,'DENY'); self.assertTrue(any('HEALTH_STALE_OR_FUTURE' in x for x in r.errors))

    def test_unregistered_fallback_denies(self):
        route=ProviderRoute('SIP','sip-a',('sip-x',))
        r=select_provider(route,[h('sip-a',False)],now=NOW,provider_registry=REG)
        self.assertEqual(r.decision,'DENY'); self.assertTrue(any('FALLBACK_PROVIDER_NOT_REGISTERED' in x for x in r.errors))

    def test_calendar_valid_open(self):
        r=validate_calendar_evidence(cal(),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'ALLOW'); self.assertTrue(r.session_open)

    def test_calendar_valid_closed(self):
        r=validate_calendar_evidence(cal(is_open=False),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'ALLOW'); self.assertFalse(r.session_open)

    def test_calendar_wrong_provider_denies(self):
        r=validate_calendar_evidence(cal('calendar-x'),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'DENY'); self.assertIn('CALENDAR_PROVIDER_NOT_REGISTERED',r.errors)

    def test_calendar_stale_denies(self):
        r=validate_calendar_evidence(cal(published=NOW-timedelta(days=30)),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'DENY'); self.assertIn('CALENDAR_EVIDENCE_STALE',r.errors)

    def test_calendar_wrong_date_denies(self):
        r=validate_calendar_evidence(cal(session=date(2026,9,18)),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'DENY'); self.assertIn('CALENDAR_SESSION_DATE_MISMATCH',r.errors)

    def test_calendar_unverified_denies(self):
        r=validate_calendar_evidence(cal(verified=False),expected_session_date=date(2026,9,19),now=NOW,provider_registry={'calendar-a'})
        self.assertEqual(r.decision,'DENY'); self.assertIn('CALENDAR_EVIDENCE_NOT_VERIFIED',r.errors)

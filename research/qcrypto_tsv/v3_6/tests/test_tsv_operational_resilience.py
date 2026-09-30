import unittest
from datetime import date, datetime, time, timedelta, timezone
from copy import deepcopy
from tests.test_tsv_policy import BASE
from tests.test_tsv_runtime import full_notice
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv
from worldshepherd_qcrypto_kms.tsv.provider_resilience import ProviderHealth, ProviderRoute, CalendarEvidence
UTC=timezone.utc
NOW=datetime(2026,9,19,2,0,tzinfo=UTC)

def state():
    s=deepcopy(BASE); s['public_notice_published_at']='2026-09-18T00:00:00Z'; s['operations_start_at']='2026-10-19T00:00:00Z'; s['issuer_notice_received_at']='2026-09-18T00:00:00Z'; s['symbol_trading_start_at']='2026-10-19T00:00:00Z'; return s

def health(pid,reach=True,part='p1'):
    return ProviderHealth('SIP',pid,reach,NOW-timedelta(seconds=1),part,True)

def calendar(provider='calendar-a'):
    return CalendarEvidence(provider,'synthetic',date(2026,9,19),True,time(13,30),time(20,0),NOW-timedelta(days=1),'a'*64,True)

class TestOperationalResilience(unittest.TestCase):
    def test_runtime_allows_healthy_primary_and_calendar(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,
            provider_route=ProviderRoute('SIP','sip-a',('sip-b',)),provider_health=[health('sip-a'),health('sip-b')],
            provider_registry={'SIP':{'sip-a','sip-b'}},require_provider_resilience=True,
            calendar_evidence=calendar(),calendar_provider_registry={'calendar-a'},require_calendar_evidence=True)
        self.assertEqual(r.decision,'ALLOW',r.to_dict())
        self.assertEqual(r.provider_failover['selected_provider_id'],'sip-a')

    def test_runtime_allows_registered_fallback(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,
            provider_route=ProviderRoute('SIP','sip-a',('sip-b',)),provider_health=[health('sip-a',False),health('sip-b')],
            provider_registry={'SIP':{'sip-a','sip-b'}},require_provider_resilience=True)
        self.assertEqual(r.decision,'ALLOW'); self.assertEqual(r.provider_failover['selected_provider_id'],'sip-b')

    def test_runtime_denies_partition(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,
            provider_route=ProviderRoute('SIP','sip-a',('sip-b',)),provider_health=[health('sip-a',True,'p1'),health('sip-b',True,'p2')],
            provider_registry={'SIP':{'sip-a','sip-b'}},require_provider_resilience=True)
        self.assertEqual(r.decision,'DENY'); self.assertIn('PROVIDER_RESILIENCE',r.failures)

    def test_runtime_denies_missing_required_calendar(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,require_calendar_evidence=True)
        self.assertEqual(r.decision,'DENY'); self.assertIn('CALENDAR_EVIDENCE',r.failures)

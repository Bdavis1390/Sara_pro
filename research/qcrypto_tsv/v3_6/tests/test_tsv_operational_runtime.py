import unittest
from datetime import datetime, timedelta, timezone

from copy import deepcopy
from tests.test_tsv_policy import BASE
from tests.test_tsv_runtime import full_notice
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv
from worldshepherd_qcrypto_kms.tsv.transaction_transparency import TransparencyFeedState

UTC=timezone.utc
T=datetime(2026,9,18,21,50,tzinfo=UTC)


def corrected_base():
    s=deepcopy(BASE)
    s["public_notice_published_at"]="2026-09-18T00:00:00Z"
    s["operations_start_at"]="2026-10-19T00:00:00Z"
    s["issuer_notice_received_at"]="2026-09-18T00:00:00Z"
    s["symbol_trading_start_at"]="2026-10-19T00:00:00Z"
    return s


class TestTsvOperationalRuntime(unittest.TestCase):
    def test_full_mode_allows(self):
        feed=TransparencyFeedState(True,True,True,True,T-timedelta(days=31),True,True,True,True)
        r=authorize_operational_tsv(corrected_base(), full_notice(), now=T, transparency_feed=feed, require_transparency_feed=True)
        self.assertEqual(r.decision,"ALLOW")
        self.assertEqual(len(r.runtime_sha256),64)

    def test_missing_required_feed_denies(self):
        r=authorize_operational_tsv(corrected_base(), full_notice(), now=T, require_transparency_feed=True)
        self.assertEqual(r.decision,"DENY")

    def test_expired_exemption_denies(self):
        r=authorize_operational_tsv(corrected_base(), full_notice(), now=datetime(2031,9,17,tzinfo=UTC))
        self.assertEqual(r.decision,"DENY")

    def test_pre_exemption_operations_start_denies_even_when_now_is_active(self):
        r=authorize_operational_tsv(BASE, full_notice(), now=T)
        self.assertEqual(r.decision,"DENY")

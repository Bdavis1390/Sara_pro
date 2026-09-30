import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib, json

from tests.test_tsv_policy import BASE
from tests.test_tsv_runtime import full_notice
from worldshepherd_qcrypto_kms.tsv.market_data_adapter import MarketDataMessage
from worldshepherd_qcrypto_kms.tsv.issuer_delivery import IssuerDeliveryReceipt
from worldshepherd_qcrypto_kms.tsv.operational_runtime import authorize_operational_tsv

UTC=timezone.utc
NOW=datetime(2026,9,18,22,50,tzinfo=UTC)
REG={"SIP":{"cta-sip"},"PRIMARY_LISTING_EXCHANGE":{"x-primary"},"LULD_PLAN":{"luld-plan"}}
NOTICE_SHA="a"*64


def state():
    s=deepcopy(BASE)
    s["public_notice_published_at"]="2026-09-18T00:00:00Z"
    s["operations_start_at"]="2026-10-19T00:00:00Z"
    s["issuer_notice_received_at"]="2026-09-18T00:00:00Z"
    s["symbol_trading_start_at"]="2026-10-19T00:00:00Z"
    return s


def m(kind="PRIMARY_LISTING_EXCHANGE",source="x-primary",status="TRADING",seq=1,payload="b"*64):
    return MarketDataMessage(kind,source,"ABC",seq,status,NOW-timedelta(seconds=2),NOW-timedelta(seconds=1),payload,True,"session-1")


def receipt(objection=None):
    d=datetime(2026,9,18,0,0,tzinfo=UTC)
    return IssuerDeliveryReceipt("ABC","issuer-1",NOTICE_SHA,"REGISTERED_EMAIL","provider-1",d,d+timedelta(minutes=1),"receipt-1","c"*64,True,objection)


class TestTsvOperationalAdversarial(unittest.TestCase):
    def test_market_and_issuer_controls_allow(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,symbol="ABC",market_messages=[m(),m("SIP","cta-sip","TRADING",1,"d"*64)],market_source_registry=REG,require_market_adapter=True,issuer_delivery_receipt=receipt(),issuer_notice_sha256=NOTICE_SHA,require_issuer_delivery=True)
        self.assertEqual(r.decision,"ALLOW",r.to_dict())
        self.assertEqual(r.market_data_batch["decision"],"ALLOW")
        self.assertEqual(r.issuer_delivery["decision"],"ALLOW")

    def test_market_conflict_denies_runtime(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,symbol="ABC",market_messages=[m(status="HALTED"),m("SIP","cta-sip","TRADING",1,"d"*64)],market_source_registry=REG,require_market_adapter=True)
        self.assertEqual(r.decision,"DENY")
        self.assertIn("MARKET_DATA_ADAPTER",r.failures)

    def test_missing_registry_denies_runtime(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,symbol="ABC",market_messages=[m()],require_market_adapter=True)
        self.assertEqual(r.decision,"DENY")

    def test_issuer_objection_denies_runtime(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,symbol="ABC",issuer_delivery_receipt=receipt(NOW-timedelta(hours=1)),issuer_notice_sha256=NOTICE_SHA,require_issuer_delivery=True)
        self.assertEqual(r.decision,"DENY")
        self.assertIn("ISSUER_DELIVERY",r.failures)

    def test_missing_issuer_context_denies_runtime(self):
        r=authorize_operational_tsv(state(),full_notice(),now=NOW,symbol="ABC",require_issuer_delivery=True)
        self.assertEqual(r.decision,"DENY")

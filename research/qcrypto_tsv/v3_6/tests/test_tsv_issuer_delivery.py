import unittest
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.issuer_delivery import IssuerDeliveryReceipt, validate_issuer_delivery

UTC=timezone.utc
NOW=datetime(2026,9,18,22,50,tzinfo=UTC)
NOTICE="a"*64


def receipt(**kw):
    base=dict(symbol="ABC",issuer_id="issuer-1",notice_sha256=NOTICE,delivery_channel="REGISTERED_EMAIL",delivery_provider_id="provider-1",delivered_at=NOW-timedelta(days=31),provider_recorded_at=NOW-timedelta(days=31)+timedelta(minutes=2),provider_receipt_id="r-1",provider_payload_sha256="b"*64,verified=True,objection_received_at=None)
    base.update(kw)
    return IssuerDeliveryReceipt(**base)


def check(r, trading=None):
    return validate_issuer_delivery(r, expected_symbol="ABC", expected_notice_sha256=NOTICE, trading_start_at=trading or NOW+timedelta(days=1), now=NOW)


class TestTsvIssuerDelivery(unittest.TestCase):
    def test_valid_receipt(self):
        r=check(receipt())
        self.assertEqual(r.decision,"ALLOW",r.errors)
        self.assertEqual(len(r.receipt_sha256),64)

    def test_absent_denies(self):
        self.assertIn("ISSUER_DELIVERY_RECEIPT_ABSENT",check(None).errors)

    def test_wrong_notice_digest_denies(self):
        self.assertIn("NOTICE_DIGEST_MISMATCH",check(receipt(notice_sha256="c"*64)).errors)

    def test_unverified_denies(self):
        self.assertIn("ISSUER_DELIVERY_NOT_VERIFIED",check(receipt(verified=False)).errors)

    def test_bad_channel_denies(self):
        self.assertIn("DELIVERY_CHANNEL_NOT_ALLOWED",check(receipt(delivery_channel="SMS")).errors)

    def test_provider_record_before_delivery_denies(self):
        d=NOW-timedelta(days=31)
        self.assertIn("PROVIDER_RECORDED_BEFORE_DELIVERY",check(receipt(delivered_at=d,provider_recorded_at=d-timedelta(seconds=1))).errors)

    def test_provider_record_delay_denies(self):
        d=NOW-timedelta(days=31)
        self.assertIn("PROVIDER_RECORD_DELAY_EXCEEDED",check(receipt(delivered_at=d,provider_recorded_at=d+timedelta(hours=2))).errors)

    def test_30_day_wait_denies(self):
        d=NOW-timedelta(days=20)
        r=receipt(delivered_at=d,provider_recorded_at=d+timedelta(minutes=1))
        self.assertIn("ISSUER_30_CALENDAR_DAY_WAIT_NOT_SATISFIED",check(r,trading=NOW+timedelta(days=1)).errors)

    def test_objection_denies(self):
        self.assertIn("ISSUER_OBJECTION_REQUIRES_HOLD",check(receipt(objection_received_at=NOW-timedelta(days=1))).errors)

    def test_future_objection_denies(self):
        r=check(receipt(objection_received_at=NOW+timedelta(days=1)))
        self.assertIn("ISSUER_OBJECTION_TIMESTAMP_IN_FUTURE",r.errors)

    def test_receipt_digest_deterministic(self):
        self.assertEqual(receipt().receipt_sha256(),receipt().receipt_sha256())
        self.assertNotEqual(receipt().receipt_sha256(),receipt(provider_receipt_id="r-2").receipt_sha256())


if __name__ == "__main__": unittest.main()

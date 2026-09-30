import unittest
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.transaction_transparency import (
    TransactionRecord, TransparencyFeedState, validate_feed, validate_transaction,
)

UTC = timezone.utc
T = datetime(2026, 9, 18, 21, 0, tzinfo=UTC)


def record(delay=5):
    return TransactionRecord(
        token_symbol="ABC", paired_asset_symbol="USDCT", price_usd="10.50", size="100",
        transaction_time_utc=T, published_at=T+timedelta(minutes=delay),
        contributed_asset="USDCT", withdrawn_asset="ABC", smart_contract_address="0xabc",
    )


class TestTsvTransactionTransparency(unittest.TestCase):
    def test_transaction_pass(self):
        self.assertEqual(validate_transaction(record())["decision"], "ALLOW")

    def test_transaction_over_ten_minutes_denies(self):
        r = validate_transaction(record(delay=11))
        self.assertEqual(r["decision"], "DENY")
        self.assertIn("PUBLICATION_DELAY_EXCEEDS_10_MINUTES", r["errors"])

    def test_publication_before_transaction_denies(self):
        x = record(); x = TransactionRecord(**{**x.__dict__, "published_at": T-timedelta(seconds=1)})
        self.assertEqual(validate_transaction(x)["decision"], "DENY")

    def test_direction_same_asset_denies(self):
        x = record(); x = TransactionRecord(**{**x.__dict__, "withdrawn_asset": "USDCT"})
        self.assertEqual(validate_transaction(x)["decision"], "DENY")

    def test_feed_passes_full_30_day_controls(self):
        f = TransparencyFeedState(True, True, True, True, T-timedelta(days=31), True, True, True, True)
        self.assertEqual(validate_feed(f, now=T)["decision"], "ALLOW")

    def test_feed_short_history_denies(self):
        f = TransparencyFeedState(True, True, True, True, T-timedelta(days=29), True, True, True, True)
        self.assertIn("HISTORY_WINDOW_SHORTER_THAN_30_DAYS", validate_feed(f, now=T)["errors"])

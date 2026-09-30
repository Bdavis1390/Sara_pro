import unittest
from datetime import datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.market_data_adapter import (
    FeedCursor, MarketDataMessage, reconcile_market_status, validate_market_message,
)

UTC=timezone.utc
NOW=datetime(2026,9,18,22,50,tzinfo=UTC)
REG={"SIP":{"cta-sip"},"PRIMARY_LISTING_EXCHANGE":{"x-primary"},"LULD_PLAN":{"luld-plan"}}


def msg(kind="PRIMARY_LISTING_EXCHANGE", source="x-primary", status="TRADING", seq=10, age=1, delay=1, payload="a"*64, symbol="ABC", session="s1"):
    obs=NOW-timedelta(seconds=age)
    return MarketDataMessage(kind,source,symbol,seq,status,obs-timedelta(seconds=delay),obs,payload,True,session)


class TestTsvMarketDataAdapter(unittest.TestCase):
    def validate(self, m, cursor=None, **kw):
        return validate_market_message(m, expected_symbol="ABC", now=NOW, source_registry=REG, cursor=cursor, **kw)

    def test_valid_registered_message(self):
        r=self.validate(msg())
        self.assertEqual(r.decision,"ALLOW")
        self.assertEqual(r.cursor.last_sequence,10)

    def test_unregistered_source_denies(self):
        self.assertIn("SOURCE_ID_NOT_REGISTERED", self.validate(msg(source="spoof")).errors)

    def test_stale_denies(self):
        self.assertIn("MESSAGE_STALE", self.validate(msg(age=31)).errors)

    def test_future_skew_denies(self):
        m=msg(age=-5,delay=0)
        self.assertIn("FUTURE_TIMESTAMP_EXCEEDS_CLOCK_SKEW", self.validate(m).errors)

    def test_observation_delay_denies(self):
        self.assertIn("OBSERVATION_DELAY_EXCEEDED", self.validate(msg(delay=11)).errors)

    def test_sequence_increment(self):
        first=self.validate(msg(seq=10)).cursor
        r=self.validate(msg(seq=11,payload="b"*64),cursor=first)
        self.assertEqual(r.decision,"ALLOW")
        self.assertEqual(r.cursor.last_sequence,11)

    def test_exact_duplicate_is_idempotent_warning(self):
        m=msg(seq=10)
        first=self.validate(m).cursor
        r=self.validate(m,cursor=first)
        self.assertEqual(r.decision,"ALLOW_WITH_WARNINGS")
        self.assertIn("EXACT_DUPLICATE_IGNORED",r.warnings)
        self.assertEqual(r.cursor,first)

    def test_same_sequence_different_hash_denies(self):
        first=self.validate(msg(seq=10)).cursor
        r=self.validate(msg(seq=10,payload="b"*64),cursor=first)
        self.assertIn("SEQUENCE_EQUIVOCATION",r.errors)

    def test_replay_denies(self):
        first=self.validate(msg(seq=10)).cursor
        self.assertIn("SEQUENCE_REPLAY_OR_REORDER", self.validate(msg(seq=9),cursor=first).errors)

    def test_gap_denies(self):
        first=self.validate(msg(seq=10)).cursor
        self.assertIn("SEQUENCE_GAP", self.validate(msg(seq=12),cursor=first).errors)

    def test_effective_time_reorder_denies(self):
        first=self.validate(msg(seq=10,age=1,delay=0)).cursor
        m=MarketDataMessage("PRIMARY_LISTING_EXCHANGE","x-primary","ABC",11,"TRADING",NOW-timedelta(seconds=20),NOW-timedelta(seconds=1),"b"*64,True,"s1")
        r=self.validate(m,cursor=first,max_observation_delay_seconds=30)
        self.assertIn("EFFECTIVE_TIME_REORDER",r.errors)

    def test_primary_halt_denies(self):
        r=reconcile_market_status([msg(status="HALTED")],expected_symbol="ABC",require_sip_for_resume=False)
        self.assertEqual(r.decision,"DENY")
        self.assertEqual(r.reason,"PRIMARY_EXCHANGE_HALT")

    def test_luld_pause_is_supplemental_fail_closed(self):
        r=reconcile_market_status([msg(),msg(kind="LULD_PLAN",source="luld-plan",status="PAUSED",seq=4,payload="c"*64)],expected_symbol="ABC")
        self.assertEqual(r.decision,"DENY")
        self.assertIn("SUPPLEMENTAL_PAUSE_GUARD_ACTIVE",r.errors)

    def test_cross_source_conflict_denies(self):
        r=reconcile_market_status([msg(status="HALTED"),msg(kind="SIP",source="cta-sip",status="TRADING",seq=4,payload="d"*64)],expected_symbol="ABC")
        self.assertIn("CROSS_SOURCE_STATUS_CONFLICT",r.errors)

    def test_resume_requires_quorum(self):
        r=reconcile_market_status([msg(status="RESUME_ELIGIBLE")],expected_symbol="ABC")
        self.assertIn("RESUME_QUORUM_INCOMPLETE",r.errors)

    def test_resume_quorum_passes(self):
        r=reconcile_market_status([msg(status="RESUME_ELIGIBLE"),msg(kind="SIP",source="cta-sip",status="RESUME_ELIGIBLE",seq=4,payload="e"*64)],expected_symbol="ABC")
        self.assertEqual(r.decision,"ALLOW",r.errors)

    def test_missing_primary_denies(self):
        r=reconcile_market_status([msg(kind="SIP",source="cta-sip",seq=4)],expected_symbol="ABC")
        self.assertIn("PRIMARY_EXCHANGE_STATUS_REQUIRED",r.errors)

    def test_source_kind_internal_conflict_denies(self):
        r=reconcile_market_status([msg(status="TRADING"),msg(status="HALTED",source="x-primary",seq=11,payload="f"*64)],expected_symbol="ABC",require_sip_for_resume=False)
        self.assertTrue(any(x.startswith("SOURCE_KIND_STATUS_CONFLICT") for x in r.errors))


if __name__ == "__main__": unittest.main()

from worldshepherd_qcrypto_kms.tsv.market_data_adapter import validate_market_batch

class TestTsvMarketDataBatch(unittest.TestCase):
    def test_ordered_two_source_stream_allows(self):
        rows=[msg(seq=10),msg(seq=11,payload="b"*64),msg(kind="SIP",source="cta-sip",seq=4,payload="c"*64),msg(kind="SIP",source="cta-sip",seq=5,payload="d"*64)]
        r=validate_market_batch(rows,expected_symbol="ABC",now=NOW,source_registry=REG,require_sip_for_resume=False)
        self.assertEqual(r.decision,"ALLOW",r.errors)
        self.assertEqual(len(r.batch_sha256),64)

    def test_batch_reorder_denies(self):
        rows=[msg(seq=10),msg(seq=9,payload="b"*64)]
        r=validate_market_batch(rows,expected_symbol="ABC",now=NOW,source_registry=REG,require_sip_for_resume=False)
        self.assertTrue(any("SEQUENCE_REPLAY_OR_REORDER" in x for x in r.errors))

    def test_batch_gap_denies(self):
        rows=[msg(seq=10),msg(seq=12,payload="b"*64)]
        r=validate_market_batch(rows,expected_symbol="ABC",now=NOW,source_registry=REG,require_sip_for_resume=False)
        self.assertTrue(any("SEQUENCE_GAP" in x for x in r.errors))

    def test_duplicate_does_not_break_batch(self):
        m=msg(seq=10)
        r=validate_market_batch([m,m],expected_symbol="ABC",now=NOW,source_registry=REG,require_sip_for_resume=False)
        self.assertEqual(r.decision,"ALLOW",r.errors)

    def test_conflicting_latest_status_denies(self):
        rows=[msg(status="HALTED"),msg(kind="SIP",source="cta-sip",status="TRADING",seq=4,payload="b"*64)]
        r=validate_market_batch(rows,expected_symbol="ABC",now=NOW,source_registry=REG)
        self.assertTrue(any("CROSS_SOURCE_STATUS_CONFLICT" in x for x in r.errors))

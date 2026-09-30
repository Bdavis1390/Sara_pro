import unittest
from datetime import datetime, timezone

from worldshepherd_qcrypto_kms.tsv.enforcement import (
    SymbolControlState,
    add_calendar_months,
    process_primary_stoppage,
    process_venue_stop,
    process_volume_observation,
)

T = datetime(2026, 9, 18, 21, 50, tzinfo=timezone.utc)


class TestEnforcement(unittest.TestCase):
    def test_calendar_month_addition(self):
        self.assertEqual(add_calendar_months(datetime(2026, 11, 30, tzinfo=timezone.utc), 3).date().isoformat(), "2027-02-28")

    def test_first_volume_breach_warns_not_pauses(self):
        s = SymbolControlState("ABC")
        r = process_volume_observation(s, exceeded=True, observed_at=T)
        self.assertEqual(r.decision, "ALLOW_WITH_WARNING")
        self.assertEqual(r.state.prior_volume_threshold_breaches, 1)
        self.assertIsNone(r.state.volume_pause_until)

    def test_second_volume_breach_pauses_three_calendar_months(self):
        s = SymbolControlState("ABC", prior_volume_threshold_breaches=1)
        r = process_volume_observation(s, exceeded=True, observed_at=T)
        self.assertEqual(r.decision, "DENY")
        self.assertEqual(r.state.volume_pause_until, datetime(2026, 12, 18, 21, 50, tzinfo=timezone.utc))
        self.assertIn("PAUSE_AFFILIATED_TSVS_SAME_STOCK", r.actions)
        self.assertIn("AMEND_PUBLIC_NOTICE_WITHIN_5_BUSINESS_DAYS", r.actions)

    def test_active_volume_pause_stays_denied(self):
        s = SymbolControlState("ABC", prior_volume_threshold_breaches=2, volume_pause_until=datetime(2026, 12, 18, tzinfo=timezone.utc))
        r = process_volume_observation(s, exceeded=False, observed_at=T)
        self.assertEqual(r.decision, "DENY")

    def test_primary_halt_concurrently_stops(self):
        s = SymbolControlState("ABC")
        r = process_primary_stoppage(s, stopped=True, observed_at=T)
        self.assertEqual(r.decision, "DENY")
        self.assertTrue(r.state.primary_halt_active)
        self.assertIn("STOP_TRADING_CONCURRENTLY", r.actions)

    def test_halt_clear_requires_explicit_resumption(self):
        s = SymbolControlState("ABC", primary_halt_active=True)
        r = process_primary_stoppage(s, stopped=False, observed_at=T, resumption_authorized=False)
        self.assertEqual(r.decision, "DENY")
        self.assertIn("HOLD_FOR_DISCLOSED_RESUMPTION_PROCEDURE", r.actions)

    def test_halt_clear_can_resume_when_no_other_stop(self):
        s = SymbolControlState("ABC", primary_halt_active=True)
        r = process_primary_stoppage(s, stopped=False, observed_at=T, resumption_authorized=True)
        self.assertEqual(r.decision, "ALLOW")
        self.assertIn("RESUME_TRADING", r.actions)

    def test_resumption_does_not_override_volume_pause(self):
        s = SymbolControlState("ABC", primary_halt_active=True, prior_volume_threshold_breaches=2, volume_pause_until=datetime(2026, 12, 18, tzinfo=timezone.utc))
        r = process_primary_stoppage(s, stopped=False, observed_at=T, resumption_authorized=True)
        self.assertEqual(r.decision, "DENY")
        self.assertIn("REMAIN_STOPPED_DUE_TO_OTHER_CONTROL", r.actions)

    def test_venue_stop_requires_notice_amendment_action(self):
        s = SymbolControlState("ABC")
        r = process_venue_stop(s, stopped=True, observed_at=T)
        self.assertEqual(r.decision, "DENY")
        self.assertIn("AMEND_PUBLIC_NOTICE_WITHIN_5_BUSINESS_DAYS", r.actions)


if __name__ == "__main__":
    unittest.main()

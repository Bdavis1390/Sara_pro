import unittest
from datetime import date, datetime, timedelta, timezone

from worldshepherd_qcrypto_kms.tsv.regulatory_clock import (
    BusinessCalendar, NoticeEvent, exemption_window_status, initial_notice_gates,
    issuer_wait_gate, revised_notice_deadline, revised_notice_gates,
)

UTC = timezone.utc


class TestTsvRegulatoryClock(unittest.TestCase):
    def test_exemption_window_active(self):
        self.assertEqual(exemption_window_status(datetime(2026, 9, 18, tzinfo=UTC))["decision"], "ALLOW")

    def test_exemption_window_fail_closed_at_end_date(self):
        self.assertEqual(exemption_window_status(datetime(2031, 9, 17, tzinfo=UTC))["decision"], "DENY")

    def test_business_day_skips_weekend(self):
        cal = BusinessCalendar()
        friday = datetime(2026, 9, 18, 12, tzinfo=UTC)
        self.assertEqual(cal.add_business_days(friday, 1).date(), date(2026, 9, 21))

    def test_business_day_skips_supplied_holiday(self):
        cal = BusinessCalendar.from_dates([date(2026, 9, 21)])
        friday = datetime(2026, 9, 18, 12, tzinfo=UTC)
        self.assertEqual(cal.add_business_days(friday, 1).date(), date(2026, 9, 22))

    def test_initial_notice_gates_pass(self):
        cal = BusinessCalendar()
        pub = datetime(2026, 9, 18, 12, tzinfo=UTC)
        ops = pub + timedelta(days=31)
        sec = datetime(2026, 9, 21, 10, tzinfo=UTC)
        rows = initial_notice_gates(published_at=pub, operations_start_at=ops, sec_notified_at=sec, now=pub, calendar=cal)
        self.assertEqual([r.status for r in rows], ["PASS", "PASS"])

    def test_initial_notice_too_late_fails(self):
        cal = BusinessCalendar()
        pub = datetime(2026, 9, 18, tzinfo=UTC)
        ops = pub + timedelta(days=29)
        rows = initial_notice_gates(published_at=pub, operations_start_at=ops, sec_notified_at=pub, now=pub, calendar=cal)
        self.assertEqual(rows[0].status, "FAIL")

    def test_issuer_wait_gate(self):
        recv = datetime(2026, 9, 18, tzinfo=UTC)
        self.assertEqual(issuer_wait_gate(issuer_received_at=recv, trading_start_at=recv+timedelta(days=30)).status, "PASS")
        self.assertEqual(issuer_wait_gate(issuer_received_at=recv, trading_start_at=recv+timedelta(days=29)).status, "FAIL")

    def test_five_business_day_revision(self):
        cal = BusinessCalendar()
        start = datetime(2026, 9, 18, tzinfo=UTC)
        due = revised_notice_deadline(event=NoticeEvent.ISSUER_OBJECTION, trigger_at=start, calendar=cal)
        self.assertEqual(due.date(), date(2026, 9, 25))

    def test_material_change_requires_20_day_advance(self):
        cal = BusinessCalendar()
        eff = datetime(2026, 11, 1, tzinfo=UTC)
        due = revised_notice_deadline(event=NoticeEvent.MATERIAL_CHANGE, trigger_at=datetime(2026, 9, 18, tzinfo=UTC), effective_at=eff, calendar=cal)
        self.assertEqual(due, eff - timedelta(days=20))

    def test_nonmaterial_quarter_due_30_calendar_days(self):
        cal = BusinessCalendar()
        due = revised_notice_deadline(event=NoticeEvent.NON_MATERIAL_QUARTER_CHANGE, trigger_at=datetime(2026, 10, 1, tzinfo=UTC), quarter_end=date(2026, 9, 30), calendar=cal)
        self.assertEqual(due.date(), date(2026, 10, 30))

    def test_missing_revision_is_pending_and_sec_clock_blocked(self):
        cal = BusinessCalendar()
        trigger = datetime(2026, 9, 18, tzinfo=UTC)
        rows = revised_notice_gates(event=NoticeEvent.ISSUER_OBJECTION, trigger_at=trigger, public_revision_at=None, sec_notified_at=None, now=trigger, calendar=cal)
        self.assertEqual(rows[0].status, "PENDING")
        self.assertEqual(rows[1].status, "BLOCKED")

# Operation-start window is separately fail-closed because a Notice can predate the exemption.
from worldshepherd_qcrypto_kms.tsv.regulatory_clock import operations_start_status

class TestTsvOperationStartWindow(unittest.TestCase):
    def test_pre_exemption_operation_start_denies(self):
        self.assertEqual(operations_start_status(datetime(2026, 9, 16, tzinfo=UTC))["decision"], "DENY")

    def test_operation_start_inside_window_allows(self):
        self.assertEqual(operations_start_status(datetime(2026, 9, 17, tzinfo=UTC))["decision"], "ALLOW")

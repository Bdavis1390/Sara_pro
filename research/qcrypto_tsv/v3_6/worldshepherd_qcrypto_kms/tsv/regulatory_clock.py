from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Iterable, Optional

EXEMPTION_START = date(2026, 9, 17)
EXEMPTION_END = date(2031, 9, 17)  # fail-closed on and after this date absent superseding authority


class NoticeEvent(str, Enum):
    STOCK_COMMENCED_OR_CEASED = "STOCK_COMMENCED_OR_CEASED"
    VOLUME_PAUSE_OR_RESUME = "VOLUME_PAUSE_OR_RESUME"
    ISSUER_OBJECTION = "ISSUER_OBJECTION"
    MATERIAL_CHANGE = "MATERIAL_CHANGE"
    NON_MATERIAL_QUARTER_CHANGE = "NON_MATERIAL_QUARTER_CHANGE"
    MATERIAL_INACCURACY_DISCOVERED = "MATERIAL_INACCURACY_DISCOVERED"


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class BusinessCalendar:
    """Business-day calendar supplied by the operator.

    Weekends are always excluded. Holidays are caller-supplied because the SEC
    order uses business-day deadlines but this package does not claim a legally
    authoritative holiday calendar.
    """

    holidays: frozenset[date] = frozenset()

    @classmethod
    def from_dates(cls, holidays: Iterable[date]) -> "BusinessCalendar":
        return cls(frozenset(holidays))

    def is_business_day(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self.holidays

    def add_business_days(self, dt: datetime, days: int) -> datetime:
        if days < 0:
            raise ValueError("days must be non-negative")
        out = _utc(dt)
        added = 0
        while added < days:
            out += timedelta(days=1)
            if self.is_business_day(out.date()):
                added += 1
        return out


@dataclass(frozen=True)
class DeadlineEvaluation:
    requirement: str
    authority: str
    deadline: datetime
    completed_at: Optional[datetime]
    status: str
    note: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["deadline"] = _utc(self.deadline).isoformat().replace("+00:00", "Z")
        data["completed_at"] = (
            _utc(self.completed_at).isoformat().replace("+00:00", "Z") if self.completed_at else None
        )
        return data


def evaluate_deadline(*, requirement: str, authority: str, deadline: datetime, completed_at: Optional[datetime], now: datetime) -> DeadlineEvaluation:
    deadline = _utc(deadline)
    now = _utc(now)
    completed = _utc(completed_at) if completed_at else None
    if completed is not None:
        ok = completed <= deadline
        return DeadlineEvaluation(requirement, authority, deadline, completed, "PASS" if ok else "FAIL", "completed within deadline" if ok else "completed after deadline")
    if now <= deadline:
        return DeadlineEvaluation(requirement, authority, deadline, None, "PENDING", "deadline has not yet elapsed")
    return DeadlineEvaluation(requirement, authority, deadline, None, "FAIL", "deadline elapsed without recorded completion")


def exemption_window_status(now: datetime) -> dict:
    d = _utc(now).date()
    active = EXEMPTION_START <= d < EXEMPTION_END
    return {
        "decision": "ALLOW" if active else "DENY",
        "active": active,
        "effective_from": EXEMPTION_START.isoformat(),
        "fail_closed_on_or_after": EXEMPTION_END.isoformat(),
        "authority": "SEC 34-106402 V / VII",
        "note": "Date-window control only; superseding SEC action must be incorporated separately.",
    }


def operations_start_status(operations_start_at: datetime) -> dict:
    d = _utc(operations_start_at).date()
    allowed = EXEMPTION_START <= d < EXEMPTION_END
    return {
        "decision": "ALLOW" if allowed else "DENY",
        "operations_start_date": d.isoformat(),
        "effective_from": EXEMPTION_START.isoformat(),
        "fail_closed_on_or_after": EXEMPTION_END.isoformat(),
        "authority": "SEC 34-106402 V / VII",
        "note": "Operation represented as relying on the exemption must begin inside the exemption window.",
    }


def initial_notice_gates(*, published_at: datetime, operations_start_at: datetime, sec_notified_at: Optional[datetime], now: datetime, calendar: BusinessCalendar) -> list[DeadlineEvaluation]:
    published_at = _utc(published_at)
    operations_start_at = _utc(operations_start_at)
    # At least 30 calendar days before operating.
    operation_deadline = operations_start_at - timedelta(days=30)
    notice_eval = evaluate_deadline(
        requirement="PUBLIC_NOTICE_AT_LEAST_30_CALENDAR_DAYS_BEFORE_OPERATION",
        authority="SEC 34-106402 II.C",
        deadline=operation_deadline,
        completed_at=published_at,
        now=now,
    )
    sec_deadline = calendar.add_business_days(published_at, 1)
    sec_eval = evaluate_deadline(
        requirement="SEC_WRITTEN_NOTICE_WITHIN_1_BUSINESS_DAY_OF_INITIAL_PUBLICATION",
        authority="SEC 34-106402 II.C",
        deadline=sec_deadline,
        completed_at=sec_notified_at,
        now=now,
    )
    return [notice_eval, sec_eval]


def issuer_wait_gate(*, issuer_received_at: datetime, trading_start_at: datetime) -> DeadlineEvaluation:
    issuer_received_at = _utc(issuer_received_at)
    deadline = issuer_received_at + timedelta(days=30)
    trading_start_at = _utc(trading_start_at)
    ok = trading_start_at >= deadline
    return DeadlineEvaluation(
        "ISSUER_NOTICE_30_CALENDAR_DAY_WAIT",
        "SEC 34-106402 II.D",
        deadline,
        trading_start_at,
        "PASS" if ok else "FAIL",
        "trading commenced after required waiting period" if ok else "trading commenced before required waiting period elapsed",
    )


def revised_notice_deadline(*, event: NoticeEvent, trigger_at: datetime, calendar: BusinessCalendar, effective_at: Optional[datetime] = None, quarter_end: Optional[date] = None) -> datetime:
    trigger_at = _utc(trigger_at)
    if event in {
        NoticeEvent.STOCK_COMMENCED_OR_CEASED,
        NoticeEvent.VOLUME_PAUSE_OR_RESUME,
        NoticeEvent.ISSUER_OBJECTION,
        NoticeEvent.MATERIAL_INACCURACY_DISCOVERED,
    }:
        return calendar.add_business_days(trigger_at, 5)
    if event == NoticeEvent.MATERIAL_CHANGE:
        if effective_at is None:
            raise ValueError("effective_at is required for MATERIAL_CHANGE")
        return _utc(effective_at) - timedelta(days=20)
    if event == NoticeEvent.NON_MATERIAL_QUARTER_CHANGE:
        if quarter_end is None:
            raise ValueError("quarter_end is required for NON_MATERIAL_QUARTER_CHANGE")
        return datetime.combine(quarter_end + timedelta(days=30), time.max, tzinfo=timezone.utc)
    raise ValueError(f"unsupported notice event: {event}")


def revised_notice_gates(*, event: NoticeEvent, trigger_at: datetime, public_revision_at: Optional[datetime], sec_notified_at: Optional[datetime], now: datetime, calendar: BusinessCalendar, effective_at: Optional[datetime] = None, quarter_end: Optional[date] = None) -> list[DeadlineEvaluation]:
    public_deadline = revised_notice_deadline(event=event, trigger_at=trigger_at, calendar=calendar, effective_at=effective_at, quarter_end=quarter_end)
    public_eval = evaluate_deadline(
        requirement=f"REVISED_PUBLIC_NOTICE:{event.value}",
        authority="SEC 34-106402 II.C / II.D / II.F",
        deadline=public_deadline,
        completed_at=public_revision_at,
        now=now,
    )
    if public_revision_at is None:
        # SEC's one-business-day clock is keyed to publication of the revised Notice;
        # fail closed on downstream readiness but do not invent a due date that has not begun.
        sec_deadline = public_deadline
        sec_eval = DeadlineEvaluation(
            "SEC_WRITTEN_NOTICE_WITHIN_1_BUSINESS_DAY_OF_REVISED_PUBLICATION",
            "SEC 34-106402 II.C",
            sec_deadline,
            None,
            "BLOCKED",
            "revised public Notice has not been recorded, so the SEC-notice clock cannot be established",
        )
    else:
        sec_deadline = calendar.add_business_days(_utc(public_revision_at), 1)
        sec_eval = evaluate_deadline(
            requirement="SEC_WRITTEN_NOTICE_WITHIN_1_BUSINESS_DAY_OF_REVISED_PUBLICATION",
            authority="SEC 34-106402 II.C",
            deadline=sec_deadline,
            completed_at=sec_notified_at,
            now=now,
        )
    return [public_eval, sec_eval]

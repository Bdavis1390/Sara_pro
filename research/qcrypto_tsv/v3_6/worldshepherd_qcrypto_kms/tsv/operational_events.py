from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class SignificantOperationalEvent:
    event_id: str
    reasonable_basis_at: datetime
    event_time: datetime
    nature: str
    systems_impacted: str
    participant_impact: str
    participants_notified_at: Optional[datetime]
    sec_notified_at: Optional[datetime]
    remediation_completed_at: Optional[datetime]
    remediation_notice_at: Optional[datetime]

    def to_dict(self) -> dict:
        out = asdict(self)
        for key in ("reasonable_basis_at", "event_time", "participants_notified_at", "sec_notified_at", "remediation_completed_at", "remediation_notice_at"):
            value = out[key]
            if value is not None:
                out[key] = _utc(value).isoformat().replace("+00:00", "Z")
        return out


def evaluate_operational_event(event: SignificantOperationalEvent, *, now: datetime) -> dict:
    errors: list[str] = []
    now = _utc(now)
    basis = _utc(event.reasonable_basis_at)
    event_time = _utc(event.event_time)
    if not event.event_id.strip():
        errors.append("EVENT_ID_MISSING")
    if not event.nature.strip() or not event.systems_impacted.strip() or not event.participant_impact.strip():
        errors.append("EVENT_NOTICE_CONTENT_INCOMPLETE")
    if basis < event_time:
        # A reasonable basis can arise at/after the event, not before the event represented here.
        pass
    if event.participants_notified_at is None:
        errors.append("PARTICIPANT_NOTICE_MISSING")
    elif _utc(event.participants_notified_at) < basis:
        errors.append("PARTICIPANT_NOTICE_PRECEDES_REASONABLE_BASIS")
    if event.sec_notified_at is None:
        errors.append("SEC_NOTICE_MISSING")
    elif event.participants_notified_at is not None and _utc(event.sec_notified_at) < basis:
        errors.append("SEC_NOTICE_PRECEDES_REASONABLE_BASIS")
    if event.remediation_completed_at is not None:
        if event.remediation_notice_at is None:
            errors.append("REMEDIATION_NOTICE_MISSING")
        elif _utc(event.remediation_notice_at) < _utc(event.remediation_completed_at):
            errors.append("REMEDIATION_NOTICE_PRECEDES_REMEDIATION_COMPLETION")
    elif event.remediation_notice_at is not None:
        errors.append("REMEDIATION_NOTICE_WITHOUT_COMPLETION")
    if event.remediation_completed_at is None and now < basis:
        errors.append("NOW_PRECEDES_REASONABLE_BASIS")
    return {
        "decision": "DENY" if errors else "ALLOW",
        "errors": errors,
        "authority": "SEC 34-106402 II.I / II.L",
        "event": event.to_dict(),
        "timing_note": "The order uses 'immediately', 'promptly', and 'as soon as reasonably practicable'; this validator does not invent numeric SLAs for those standards.",
    }

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import calendar
from typing import Any, Dict, List, Optional


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def add_calendar_months(dt: datetime, months: int) -> datetime:
    """Add calendar months while clamping the day to the target month."""
    dt = _utc(dt)
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


@dataclass(frozen=True)
class SymbolControlState:
    symbol: str
    prior_volume_threshold_breaches: int = 0
    volume_pause_until: Optional[datetime] = None
    primary_halt_active: bool = False
    venue_stop_active: bool = False
    resumption_authorized: bool = False

    def trading_permitted(self, *, now: datetime) -> bool:
        now = _utc(now)
        volume_paused = self.volume_pause_until is not None and now < _utc(self.volume_pause_until)
        return not volume_paused and not self.primary_halt_active and not self.venue_stop_active


@dataclass(frozen=True)
class EnforcementResult:
    state: SymbolControlState
    decision: str
    actions: List[str]
    authority: str
    note: str

    def to_dict(self) -> Dict[str, Any]:
        state = asdict(self.state)
        if self.state.volume_pause_until is not None:
            state["volume_pause_until"] = _utc(self.state.volume_pause_until).isoformat().replace("+00:00", "Z")
        return {
            "state": state,
            "decision": self.decision,
            "actions": list(self.actions),
            "authority": self.authority,
            "note": self.note,
        }


def process_volume_observation(
    state: SymbolControlState,
    *,
    exceeded: bool,
    observed_at: datetime,
) -> EnforcementResult:
    observed_at = _utc(observed_at)
    if not exceeded:
        decision = "DENY" if not state.trading_permitted(now=observed_at) else "ALLOW"
        return EnforcementResult(state, decision, [], "SEC 34-106402 II.F", "No new volume-threshold exceedance observed.")

    if state.prior_volume_threshold_breaches == 0:
        new_state = replace(state, prior_volume_threshold_breaches=1)
        return EnforcementResult(
            new_state,
            "ALLOW_WITH_WARNING" if new_state.trading_permitted(now=observed_at) else "DENY",
            ["RECORD_FIRST_THRESHOLD_EXCEEDANCE", "ENFORCE_NO_FURTHER_THRESHOLD_EXCEEDANCE"],
            "SEC 34-106402 II.F",
            "First exceedance does not itself trigger the three-month pause; future exceedances must not occur.",
        )

    pause_until = add_calendar_months(observed_at, 3)
    new_state = replace(
        state,
        prior_volume_threshold_breaches=state.prior_volume_threshold_breaches + 1,
        volume_pause_until=pause_until,
        resumption_authorized=False,
    )
    return EnforcementResult(
        new_state,
        "DENY",
        [
            "PAUSE_TRADING_IMMEDIATELY",
            "PAUSE_AFFILIATED_TSVS_SAME_STOCK",
            "NOTIFY_PARTICIPANTS_IMMEDIATELY",
            "AMEND_PUBLIC_NOTICE_WITHIN_5_BUSINESS_DAYS",
            "RECORD_PAUSE_EVIDENCE",
        ],
        "SEC 34-106402 II.F",
        "Subsequent volume-threshold exceedance triggers a three-calendar-month pause from the exceedance date.",
    )


def process_primary_stoppage(
    state: SymbolControlState,
    *,
    stopped: bool,
    observed_at: datetime,
    resumption_authorized: bool = False,
) -> EnforcementResult:
    observed_at = _utc(observed_at)
    if stopped:
        new_state = replace(state, primary_halt_active=True, resumption_authorized=False)
        return EnforcementResult(
            new_state,
            "DENY",
            ["STOP_TRADING_CONCURRENTLY", "NOTIFY_PARTICIPANTS_IMMEDIATELY", "RECORD_STOPPAGE_EVIDENCE"],
            "SEC 34-106402 II.H",
            "Primary-listing-exchange stoppage is active.",
        )

    # A feed saying "not stopped" is not enough to override disclosed resumption controls.
    new_state = replace(state, primary_halt_active=False, resumption_authorized=bool(resumption_authorized))
    if not resumption_authorized:
        return EnforcementResult(
            new_state,
            "DENY",
            ["HOLD_FOR_DISCLOSED_RESUMPTION_PROCEDURE"],
            "SEC 34-106402 II.H / III.cc",
            "Underlying stoppage cleared, but explicit resumption authorization is absent.",
        )
    decision = "ALLOW" if new_state.trading_permitted(now=observed_at) else "DENY"
    actions = ["RESUME_TRADING"] if decision == "ALLOW" else ["REMAIN_STOPPED_DUE_TO_OTHER_CONTROL"]
    return EnforcementResult(
        new_state,
        decision,
        actions,
        "SEC 34-106402 II.H / III.cc",
        "Underlying stoppage cleared and disclosed resumption control authorized; other stops still apply.",
    )


def process_venue_stop(
    state: SymbolControlState,
    *,
    stopped: bool,
    observed_at: datetime,
    resumption_authorized: bool = False,
) -> EnforcementResult:
    observed_at = _utc(observed_at)
    if stopped:
        new_state = replace(state, venue_stop_active=True, resumption_authorized=False)
        return EnforcementResult(
            new_state,
            "DENY",
            ["STOP_TRADING", "NOTIFY_PARTICIPANTS_IMMEDIATELY", "AMEND_PUBLIC_NOTICE_WITHIN_5_BUSINESS_DAYS", "RECORD_STOPPAGE_EVIDENCE"],
            "SEC 34-106402 II.H / II.C",
            "TSV-initiated stop is active.",
        )
    new_state = replace(state, venue_stop_active=False, resumption_authorized=bool(resumption_authorized))
    if not resumption_authorized:
        return EnforcementResult(new_state, "DENY", ["HOLD_FOR_DISCLOSED_RESUMPTION_PROCEDURE"], "SEC 34-106402 III.cc", "Venue stop cleared but resumption authorization is absent.")
    decision = "ALLOW" if new_state.trading_permitted(now=observed_at) else "DENY"
    return EnforcementResult(new_state, decision, ["RESUME_TRADING"] if decision == "ALLOW" else ["REMAIN_STOPPED_DUE_TO_OTHER_CONTROL"], "SEC 34-106402 III.cc", "Venue stop cleared under explicit resumption authorization; other stops still apply.")

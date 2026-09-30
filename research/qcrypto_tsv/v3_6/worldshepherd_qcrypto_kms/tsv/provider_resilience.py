"""Provider health, failover, partition, and source-bound calendar controls.

These controls model and test operational resilience. Provider identities and calendar
records are operator-supplied evidence; they are not claims of licensed or authoritative
connectivity unless independently validated outside this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timezone
import hashlib
import json
import re
from typing import Any, Mapping, Optional, Sequence

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _utc(v: datetime) -> datetime:
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.astimezone(timezone.utc)


def _canon(v: Any) -> bytes:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True)
class ProviderHealth:
    source_kind: str
    provider_id: str
    reachable: bool
    observed_at: datetime
    partition_id: str
    verified: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["observed_at"] = _utc(self.observed_at).isoformat().replace("+00:00", "Z")
        return d


@dataclass(frozen=True)
class ProviderRoute:
    source_kind: str
    primary_provider_id: str
    fallback_provider_ids: tuple[str, ...]


@dataclass(frozen=True)
class FailoverDecision:
    decision: str
    selected_provider_id: Optional[str]
    reason: str
    errors: tuple[str, ...]
    evidence_sha256: str
    claims_label: str = "SYNTHETIC_PROVIDER_RESILIENCE_DECISION_ONLY"

    def to_dict(self) -> dict:
        return asdict(self)


def select_provider(
    route: ProviderRoute,
    health: Sequence[ProviderHealth],
    *,
    now: datetime,
    provider_registry: Mapping[str, set[str] | frozenset[str]],
    max_health_age_seconds: int = 15,
    deny_on_partition_disagreement: bool = True,
) -> FailoverDecision:
    errors: list[str] = []
    now_u = _utc(now)
    allowed = provider_registry.get(route.source_kind, set())
    if route.primary_provider_id not in allowed:
        errors.append("PRIMARY_PROVIDER_NOT_REGISTERED")
    for p in route.fallback_provider_ids:
        if p not in allowed:
            errors.append(f"FALLBACK_PROVIDER_NOT_REGISTERED:{p}")

    latest: dict[str, ProviderHealth] = {}
    for row in health:
        if row.source_kind != route.source_kind:
            continue
        if row.provider_id not in allowed:
            errors.append(f"HEALTH_PROVIDER_NOT_REGISTERED:{row.provider_id}")
            continue
        if not row.verified:
            errors.append(f"HEALTH_NOT_VERIFIED:{row.provider_id}")
            continue
        age = (now_u - _utc(row.observed_at)).total_seconds()
        if age < -2 or age > max_health_age_seconds:
            errors.append(f"HEALTH_STALE_OR_FUTURE:{row.provider_id}")
            continue
        prev = latest.get(row.provider_id)
        if prev is None or _utc(row.observed_at) > _utc(prev.observed_at):
            latest[row.provider_id] = row

    reachable = [r for r in latest.values() if r.reachable]
    if deny_on_partition_disagreement and len({r.partition_id for r in reachable}) > 1:
        errors.append("PROVIDER_PARTITION_DISAGREEMENT")

    selected: Optional[str] = None
    reason = "NO_HEALTHY_PROVIDER"
    primary = latest.get(route.primary_provider_id)
    if primary and primary.reachable:
        selected = primary.provider_id
        reason = "PRIMARY_HEALTHY"
    else:
        for pid in route.fallback_provider_ids:
            row = latest.get(pid)
            if row and row.reachable:
                selected = pid
                reason = "FAILOVER_TO_REGISTERED_FALLBACK"
                break
        if selected is None:
            errors.append("NO_REACHABLE_REGISTERED_PROVIDER")

    if errors:
        selected = None
        reason = "FAIL_CLOSED"
    material = {
        "source_kind": route.source_kind,
        "primary": route.primary_provider_id,
        "fallbacks": route.fallback_provider_ids,
        "health": [r.to_dict() for r in sorted(health, key=lambda x: (x.provider_id, _utc(x.observed_at)))],
        "selected": selected,
        "reason": reason,
        "errors": sorted(errors),
    }
    digest = hashlib.sha256(b"WS-TSV-PROVIDER-FAILOVER-V1\x00" + _canon(material)).hexdigest()
    return FailoverDecision("DENY" if errors else "ALLOW", selected, reason, tuple(errors), digest)


@dataclass(frozen=True)
class CalendarEvidence:
    provider_id: str
    calendar_id: str
    session_date: date
    is_open: bool
    regular_open_utc: Optional[time]
    regular_close_utc: Optional[time]
    published_at: datetime
    payload_sha256: str
    verified: bool = True

    def to_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "calendar_id": self.calendar_id,
            "session_date": self.session_date.isoformat(),
            "is_open": self.is_open,
            "regular_open_utc": self.regular_open_utc.isoformat() if self.regular_open_utc else None,
            "regular_close_utc": self.regular_close_utc.isoformat() if self.regular_close_utc else None,
            "published_at": _utc(self.published_at).isoformat().replace("+00:00", "Z"),
            "payload_sha256": self.payload_sha256,
            "verified": self.verified,
        }


@dataclass(frozen=True)
class CalendarDecision:
    decision: str
    session_open: Optional[bool]
    errors: tuple[str, ...]
    evidence_sha256: str
    claims_label: str = "SOURCE_BOUND_CALENDAR_EVIDENCE_ONLY_NOT_AUTHORITATIVE_MARKET_CALENDAR"

    def to_dict(self) -> dict:
        return asdict(self)


def validate_calendar_evidence(
    evidence: CalendarEvidence,
    *,
    expected_session_date: date,
    now: datetime,
    provider_registry: set[str] | frozenset[str],
    max_publication_age_days: int = 14,
) -> CalendarDecision:
    errors: list[str] = []
    if evidence.provider_id not in provider_registry:
        errors.append("CALENDAR_PROVIDER_NOT_REGISTERED")
    if not evidence.calendar_id.strip():
        errors.append("CALENDAR_ID_EMPTY")
    if evidence.session_date != expected_session_date:
        errors.append("CALENDAR_SESSION_DATE_MISMATCH")
    if not evidence.verified:
        errors.append("CALENDAR_EVIDENCE_NOT_VERIFIED")
    if not HEX64.fullmatch(evidence.payload_sha256):
        errors.append("CALENDAR_PAYLOAD_SHA256_MALFORMED")
    age = (_utc(now) - _utc(evidence.published_at)).total_seconds()
    if age < -2:
        errors.append("CALENDAR_PUBLISHED_IN_FUTURE")
    if age > max_publication_age_days * 86400:
        errors.append("CALENDAR_EVIDENCE_STALE")
    if evidence.is_open:
        if evidence.regular_open_utc is None or evidence.regular_close_utc is None:
            errors.append("OPEN_SESSION_HOURS_MISSING")
        elif evidence.regular_open_utc >= evidence.regular_close_utc:
            errors.append("OPEN_SESSION_HOURS_INVALID")
    else:
        if evidence.regular_open_utc is not None or evidence.regular_close_utc is not None:
            errors.append("CLOSED_SESSION_SHOULD_NOT_HAVE_REGULAR_HOURS")
    material = evidence.to_dict() | {"expected_session_date": expected_session_date.isoformat(), "errors": sorted(errors)}
    digest = hashlib.sha256(b"WS-TSV-CALENDAR-EVIDENCE-V1\x00" + _canon(material)).hexdigest()
    return CalendarDecision("DENY" if errors else "ALLOW", None if errors else evidence.is_open, tuple(errors), digest)

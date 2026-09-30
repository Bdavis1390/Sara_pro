from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Any, Dict, Optional


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class SourceEvidence:
    symbol: str
    source_kind: str
    source_id: str
    observed_at: datetime
    effective_at: datetime
    payload_sha256: str
    verified: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["observed_at"] = _utc(self.observed_at).isoformat().replace("+00:00", "Z")
        d["effective_at"] = _utc(self.effective_at).isoformat().replace("+00:00", "Z")
        return d


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return _utc(dt)


def source_evidence_from_dict(data: Dict[str, Any]) -> SourceEvidence:
    return SourceEvidence(
        symbol=str(data["symbol"]),
        source_kind=str(data["source_kind"]),
        source_id=str(data["source_id"]),
        observed_at=_parse_dt(str(data["observed_at"])),
        effective_at=_parse_dt(str(data["effective_at"])),
        payload_sha256=str(data["payload_sha256"]),
        verified=bool(data["verified"]),
    )


@dataclass(frozen=True)
class SourceEvidenceResult:
    decision: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


def validate_source_evidence(
    evidence: Optional[SourceEvidence],
    *,
    expected_symbol: str,
    now: datetime,
    max_age_seconds: int,
    allowed_source_kinds: set[str],
) -> SourceEvidenceResult:
    """Fail closed on absent, unverified, mismatched, future, or stale evidence."""
    if evidence is None:
        return SourceEvidenceResult("DENY", "source evidence is absent")
    if not evidence.verified:
        return SourceEvidenceResult("DENY", "source evidence is not verified")
    if evidence.symbol.upper() != expected_symbol.upper():
        return SourceEvidenceResult("DENY", "source evidence symbol mismatch")
    if evidence.source_kind not in allowed_source_kinds:
        return SourceEvidenceResult("DENY", "source kind is not authorized")
    if not evidence.source_id.strip():
        return SourceEvidenceResult("DENY", "source identifier is empty")
    if not _SHA256_RE.fullmatch(evidence.payload_sha256):
        return SourceEvidenceResult("DENY", "payload SHA-256 is malformed")
    now_u = _utc(now)
    observed = _utc(evidence.observed_at)
    effective = _utc(evidence.effective_at)
    if observed > now_u or effective > now_u:
        return SourceEvidenceResult("DENY", "source evidence timestamp is in the future")
    age = (now_u - observed).total_seconds()
    if age > max_age_seconds:
        return SourceEvidenceResult("DENY", f"source evidence is stale ({int(age)}s > {max_age_seconds}s)")
    return SourceEvidenceResult("ALLOW", "source evidence passes bounded freshness/provenance checks")

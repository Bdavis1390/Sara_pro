"""Canonical validation helpers for WS-CAE continuity artifacts."""

from __future__ import annotations

from datetime import date, datetime
import re

_CONTENT_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def valid_content_id(value: str) -> bool:
    """Return True only for canonical lowercase SHA-256 content identifiers."""
    return isinstance(value, str) and bool(_CONTENT_ID_RE.fullmatch(value))


def valid_date(value: str) -> bool:
    """Validate canonical ISO calendar dates in YYYY-MM-DD form."""
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def valid_datetime(value: str) -> bool:
    """Validate an ISO-8601 datetime with an explicit timezone offset or Z."""
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return parsed.tzinfo is not None

from __future__ import annotations

from datetime import date


def valid_revision(value: object) -> bool:
    return type(value) is int and value >= 1


def valid_as_of(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False

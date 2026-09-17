#!/usr/bin/env python3
"""Fail-closed integrity controls for WS-QPHONON evidence events.

This module validates software evidence integrity only. It does not establish
physical quantum capability, authenticate a human identity, or actuate hardware.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import uuid
from typing import Any, Iterable

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ECHO_SCHEMA = "WS-QPHONON-ECHO-EVENT-V0.2"

EXPECTED_ECHO_KEYS = {
    "schema",
    "event_id",
    "event_sequence",
    "event_time_utc",
    "raw_data_hash",
    "config_digest",
    "previous_event_digest",
    "event_digest",
    "model_version",
    "prior",
    "posterior",
    "experiment_proposed",
    "expected_information_gain",
    "prime_decision",
    "control_waveform_or_parameters",
    "environmental_state",
    "measurement_result",
    "model_discrepancy",
    "claims_state",
}


@dataclass(frozen=True)
class SecurityDecision:
    passed: bool
    disposition: str
    reasons: list[str]


def is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def compute_event_digest(event: dict[str, Any]) -> str:
    material = dict(event)
    material.pop("event_digest", None)
    return sha256_json(material)


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    if parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed.astimezone(timezone.utc)


def verify_echo_event(
    event: dict[str, Any],
    *,
    expected_config_digest: str,
    expected_previous_event_digest: str,
    seen_event_ids: Iterable[str] = (),
    now: datetime | None = None,
    max_age_seconds: int = 300,
    max_future_skew_seconds: int = 30,
) -> SecurityDecision:
    reasons: list[str] = []
    now = now or datetime.now(timezone.utc)

    unknown = sorted(set(event) - EXPECTED_ECHO_KEYS)
    missing = sorted(EXPECTED_ECHO_KEYS - set(event))
    if unknown:
        reasons.append("UNKNOWN_TOP_LEVEL_FIELDS")
    if missing:
        reasons.append("MISSING_REQUIRED_FIELDS")

    if event.get("schema") != ECHO_SCHEMA:
        reasons.append("SCHEMA_MISMATCH")

    event_id = event.get("event_id")
    try:
        parsed_id = uuid.UUID(str(event_id))
        if parsed_id.version != 4 or str(parsed_id) != event_id:
            reasons.append("EVENT_ID_NOT_CANONICAL_UUID4")
    except (ValueError, TypeError, AttributeError):
        reasons.append("EVENT_ID_INVALID")

    if event_id in set(seen_event_ids):
        reasons.append("EVENT_REPLAY_DETECTED")

    sequence = event.get("event_sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        reasons.append("EVENT_SEQUENCE_INVALID")

    timestamp = _parse_utc(event.get("event_time_utc"))
    if timestamp is None:
        reasons.append("EVENT_TIME_INVALID")
    else:
        age = (now - timestamp).total_seconds()
        if age > max_age_seconds:
            reasons.append("EVENT_STALE")
        if age < -max_future_skew_seconds:
            reasons.append("EVENT_FROM_FUTURE")

    for field in (
        "raw_data_hash",
        "config_digest",
        "previous_event_digest",
        "event_digest",
    ):
        if not _is_hex64(event.get(field)):
            reasons.append(f"{field.upper()}_INVALID")

    if _is_hex64(event.get("config_digest")) and event["config_digest"] != expected_config_digest:
        reasons.append("CONFIG_DIGEST_MISMATCH")

    if (
        _is_hex64(event.get("previous_event_digest"))
        and event["previous_event_digest"] != expected_previous_event_digest
    ):
        reasons.append("EVENT_CHAIN_MISMATCH")

    try:
        calculated = compute_event_digest(event)
    except (TypeError, ValueError, OverflowError):
        reasons.append("EVENT_CANONICALIZATION_FAILED")
    else:
        if _is_hex64(event.get("event_digest")) and event["event_digest"] != calculated:
            reasons.append("EVENT_DIGEST_MISMATCH")

    passed = not reasons
    return SecurityDecision(
        passed=passed,
        disposition="INTEGRITY_VERIFIED" if passed else "REJECT_EVIDENCE",
        reasons=reasons,
    )


def to_dict(decision: SecurityDecision) -> dict[str, Any]:
    return asdict(decision)

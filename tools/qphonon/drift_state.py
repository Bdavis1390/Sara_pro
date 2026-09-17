#!/usr/bin/env python3
"""Passive OVERWATCH drift classification for WS-QPHONON L2.

This module does not actuate hardware, retune devices, or authorize experiments.
It compares an observed state with a validated envelope and returns either
WITHIN_ENVELOPE or the configured fallback mode (normally CHARACTERIZE).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class DriftDecision:
    within_envelope: bool
    disposition: str
    violations: list[str]
    missing: list[str]


def _check_bounds(name: str, value: Any, bounds: dict[str, Any], violations: list[str]) -> None:
    if not isinstance(value, (int, float)):
        violations.append(f"{name}:NON_NUMERIC")
        return
    minimum = bounds.get("min")
    maximum = bounds.get("max")
    if isinstance(minimum, (int, float)) and float(value) < float(minimum):
        violations.append(f"{name}:BELOW_MIN")
    if isinstance(maximum, (int, float)) and float(value) > float(maximum):
        violations.append(f"{name}:ABOVE_MAX")


def evaluate(config: dict[str, Any], snapshot: dict[str, Any], envelope: dict[str, Any]) -> DriftDecision:
    """Classify drift without attempting compensation.

    Only variables present in the supplied validated envelope are evaluated.
    Missing observed values force fallback to characterization.
    """
    overwatch = config.get("overwatch", {})
    fallback = str(overwatch.get("fallback_mode", "CHARACTERIZE"))
    tracked = set(overwatch.get("track_fast_state", [])) | set(overwatch.get("track_slow_state", []))

    violations: list[str] = []
    missing: list[str] = []

    for name, bounds in envelope.items():
        if name not in tracked:
            violations.append(f"{name}:UNTRACKED_ENVELOPE_FIELD")
            continue
        if name not in snapshot or snapshot[name] is None:
            missing.append(name)
            continue
        if not isinstance(bounds, dict):
            violations.append(f"{name}:INVALID_BOUNDS")
            continue
        _check_bounds(name, snapshot[name], bounds, violations)

    within = not violations and not missing
    return DriftDecision(
        within_envelope=within,
        disposition="WITHIN_ENVELOPE" if within else fallback,
        violations=violations,
        missing=missing,
    )


def to_dict(decision: DriftDecision) -> dict[str, Any]:
    return asdict(decision)

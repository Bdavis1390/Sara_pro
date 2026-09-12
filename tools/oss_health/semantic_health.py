"""Semantic service health primitives for upstream resilience test harnesses.

This module intentionally distinguishes process liveness from useful service
readiness.  It is small and dependency-free so it can be embedded in ROS 2,
Zenoh, simulator, or CI probes without coupling an upstream project to
Worldshepherd-specific infrastructure.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class HealthState(str, Enum):
    """Externally meaningful health state."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class HealthSample:
    """Inputs used to determine semantic readiness.

    `process_alive` answers only whether the process exists.
    `endpoint_accepting` should be established with a real connection or
    round-trip probe rather than a LISTEN-socket check.
    `telemetry_age_seconds` is None when no telemetry has been observed.
    `operational_entities` / `expected_min_entities` are optional and useful
    for fleet-style systems where a process may be alive with no usable robots.
    """

    process_alive: bool
    endpoint_accepting: bool
    telemetry_age_seconds: Optional[float]
    telemetry_max_age_seconds: float
    operational_entities: Optional[int] = None
    expected_min_entities: Optional[int] = None


@dataclass(frozen=True)
class HealthAssessment:
    state: HealthState
    reasons: Tuple[str, ...]
    process_alive: bool
    service_ready: bool


def assess(sample: HealthSample) -> HealthAssessment:
    """Evaluate a health sample with deterministic precedence.

    Precedence is UNAVAILABLE > STALE > DEGRADED > HEALTHY.  A stale service is
    called out separately because frozen telemetry is a common silent-failure
    mode even while the process and middleware remain alive.
    """

    if sample.telemetry_max_age_seconds < 0:
        raise ValueError("telemetry_max_age_seconds must be non-negative")
    if sample.telemetry_age_seconds is not None and sample.telemetry_age_seconds < 0:
        raise ValueError("telemetry_age_seconds must be non-negative")
    if sample.operational_entities is not None and sample.operational_entities < 0:
        raise ValueError("operational_entities must be non-negative")
    if sample.expected_min_entities is not None and sample.expected_min_entities < 0:
        raise ValueError("expected_min_entities must be non-negative")

    if not sample.process_alive:
        return HealthAssessment(
            state=HealthState.UNAVAILABLE,
            reasons=("process_not_alive",),
            process_alive=False,
            service_ready=False,
        )

    reasons = []

    if not sample.endpoint_accepting:
        reasons.append("endpoint_not_accepting")

    stale = sample.telemetry_age_seconds is None or (
        sample.telemetry_age_seconds > sample.telemetry_max_age_seconds
    )
    if stale:
        reasons.append(
            "telemetry_missing"
            if sample.telemetry_age_seconds is None
            else "telemetry_stale"
        )

    if (
        sample.expected_min_entities is not None
        and sample.operational_entities is not None
        and sample.operational_entities < sample.expected_min_entities
    ):
        reasons.append("operational_entity_count_below_minimum")

    if not reasons:
        state = HealthState.HEALTHY
    elif stale:
        state = HealthState.STALE
    else:
        state = HealthState.DEGRADED

    return HealthAssessment(
        state=state,
        reasons=tuple(reasons),
        process_alive=True,
        service_ready=(state == HealthState.HEALTHY),
    )

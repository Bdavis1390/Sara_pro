from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .pba_models import OperatingState, PBAObservation, PBAState, SafeToBeamAuthorization


class PBATransitionError(RuntimeError):
    pass


LEGAL_TRANSITIONS: dict[PBAState, frozenset[PBAState]] = {
    PBAState.SAFE_OFF: frozenset({PBAState.DISCOVERY}),
    PBAState.DISCOVERY: frozenset({PBAState.ATTESTED, PBAState.SAFE_HOLD, PBAState.SAFE_OFF}),
    PBAState.ATTESTED: frozenset({PBAState.STATE_VALIDATION, PBAState.SAFE_HOLD, PBAState.SAFE_OFF}),
    PBAState.STATE_VALIDATION: frozenset(
        {PBAState.AUTHORIZATION_PENDING, PBAState.SAFE_HOLD, PBAState.SAFE_OFF}
    ),
    PBAState.AUTHORIZATION_PENDING: frozenset(
        {PBAState.VERIFY_ONLY, PBAState.SAFE_OFF, PBAState.SAFE_HOLD}
    ),
    PBAState.VERIFY_ONLY: frozenset(
        {PBAState.DELIVERY_AUTHORIZED, PBAState.RAMP_DOWN, PBAState.SAFE_HOLD, PBAState.SAFE_OFF}
    ),
    PBAState.DELIVERY_AUTHORIZED: frozenset(
        {PBAState.RAMP_DOWN, PBAState.FAULT_LATCHED}
    ),
    PBAState.RAMP_DOWN: frozenset({PBAState.SAFE_OFF, PBAState.FAULT_LATCHED}),
    PBAState.SAFE_HOLD: frozenset({PBAState.STATE_VALIDATION, PBAState.SAFE_OFF}),
    PBAState.FAULT_LATCHED: frozenset({PBAState.SAFE_OFF}),
}


@dataclass(frozen=True, slots=True)
class PBADecision:
    permitted: bool
    reason: str


def can_transition(current: PBAState, requested: PBAState) -> bool:
    return requested in LEGAL_TRANSITIONS[current]


def require_transition(current: PBAState, requested: PBAState) -> None:
    if not can_transition(current, requested):
        raise PBATransitionError(f"prohibited WS-PBA transition: {current} -> {requested}")


def evaluate_delivery_authorization(
    token: SafeToBeamAuthorization,
    observation: PBAObservation,
    *,
    now: datetime | None = None,
) -> PBADecision:
    """Evaluate assurance invariants without driving partner hardware.

    This function intentionally performs only authorization/assurance checks. A
    positive result means the requested bounded state is permissible; it is not
    a physical beam-control command.
    """

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    if token.allowed_state is not OperatingState.DELIVERY_AUTHORIZED:
        return PBADecision(False, "TOKEN_NOT_DELIVERY_AUTHORIZATION")
    if not (token.valid_from <= now <= token.valid_until):
        return PBADecision(False, "AUTHORIZATION_OUTSIDE_VALIDITY_WINDOW")
    if token.transmitter_id != observation.transmitter_id:
        return PBADecision(False, "TRANSMITTER_ID_MISMATCH")
    if token.receiver_id != observation.receiver_id:
        return PBADecision(False, "RECEIVER_ID_MISMATCH")
    if not observation.transmitter_attested:
        return PBADecision(False, "TRANSMITTER_NOT_ATTESTED")
    if not observation.receiver_attested:
        return PBADecision(False, "RECEIVER_NOT_ATTESTED")
    if observation.identity_changed:
        return PBADecision(False, "IDENTITY_CHANGED")
    if observation.configuration_changed:
        return PBADecision(False, "CONFIGURATION_CHANGED")
    if token.configuration_digest != observation.configuration_digest:
        return PBADecision(False, "CONFIGURATION_DIGEST_MISMATCH")
    if not observation.navigation_valid:
        return PBADecision(False, "NAVIGATION_INVALID")
    if token.navigation_digest != observation.navigation_digest:
        return PBADecision(False, "NAVIGATION_DIGEST_MISMATCH")
    if not observation.tracking_valid:
        return PBADecision(False, "TRACKING_INVALID")
    if token.tracking_digest != observation.tracking_digest:
        return PBADecision(False, "TRACKING_DIGEST_MISMATCH")
    if not observation.telemetry_fresh:
        return PBADecision(False, "TELEMETRY_STALE")
    if observation.critical_state_disagreement:
        return PBADecision(False, "CRITICAL_STATE_DISAGREEMENT")
    if observation.safety_veto:
        return PBADecision(False, "SAFETY_VETO")

    return PBADecision(True, "DELIVERY_AUTHORIZED")


def fault_disposition(observation: PBAObservation) -> PBAState:
    """Return the fail-safe disposition for an observation during operation."""

    if (
        observation.safety_veto
        or observation.identity_changed
        or observation.configuration_changed
        or not observation.transmitter_attested
        or not observation.receiver_attested
    ):
        return PBAState.FAULT_LATCHED
    if (
        not observation.telemetry_fresh
        or not observation.navigation_valid
        or not observation.tracking_valid
        or observation.critical_state_disagreement
    ):
        return PBAState.RAMP_DOWN
    return PBAState.DELIVERY_AUTHORIZED

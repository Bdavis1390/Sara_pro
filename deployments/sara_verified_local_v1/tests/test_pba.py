from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from worldshepherd_sara.pba_evidence import (
    GENESIS_HASH,
    PBAEvidenceEvent,
    seal_event,
    verify_chain,
)
from worldshepherd_sara.pba_models import (
    OperatingState,
    PBAObservation,
    PBAState,
    SafeToBeamAuthorization,
)
from worldshepherd_sara.pba_state_machine import (
    PBATransitionError,
    can_transition,
    evaluate_delivery_authorization,
    fault_disposition,
    require_transition,
)


D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def token(now: datetime | None = None) -> SafeToBeamAuthorization:
    now = now or datetime.now(timezone.utc)
    return SafeToBeamAuthorization(
        authorization_id=uuid4(),
        mission_id="PBA-G1-TEST",
        transmitter_id="tx-001",
        receiver_id="rx-001",
        transmitter_attestation="attest-tx",
        receiver_attestation="attest-rx",
        configuration_digest=D1,
        navigation_digest=D2,
        tracking_digest=D3,
        valid_from=now - timedelta(minutes=1),
        valid_until=now + timedelta(minutes=5),
        allowed_state=OperatingState.DELIVERY_AUTHORIZED,
        policy_id="PBA-TEST-01",
        authority_id="PRIME-TEST",
        previous_event_hash=D0,
        nonce="0123456789abcdef",
        sequence=1,
        signature="g1-placeholder-signature",
    )


def observation(**updates: object) -> PBAObservation:
    values: dict[str, object] = {
        "transmitter_id": "tx-001",
        "receiver_id": "rx-001",
        "configuration_digest": D1,
        "navigation_digest": D2,
        "tracking_digest": D3,
        "transmitter_attested": True,
        "receiver_attested": True,
        "navigation_valid": True,
        "tracking_valid": True,
        "telemetry_fresh": True,
        "safety_veto": False,
        "critical_state_disagreement": False,
        "configuration_changed": False,
        "identity_changed": False,
    }
    values.update(updates)
    return PBAObservation(**values)


def test_delivery_requires_verify_only_predecessor() -> None:
    prohibited = {
        PBAState.SAFE_OFF,
        PBAState.DISCOVERY,
        PBAState.ATTESTED,
        PBAState.STATE_VALIDATION,
        PBAState.AUTHORIZATION_PENDING,
        PBAState.SAFE_HOLD,
        PBAState.FAULT_LATCHED,
        PBAState.RAMP_DOWN,
    }
    for current in prohibited:
        assert not can_transition(current, PBAState.DELIVERY_AUTHORIZED)
    assert can_transition(PBAState.VERIFY_ONLY, PBAState.DELIVERY_AUTHORIZED)


def test_require_transition_rejects_shortcut() -> None:
    with pytest.raises(PBATransitionError):
        require_transition(PBAState.DISCOVERY, PBAState.DELIVERY_AUTHORIZED)


def test_nominal_delivery_authorization_passes() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_delivery_authorization(token(now), observation(), now=now)
    assert decision.permitted is True
    assert decision.reason == "DELIVERY_AUTHORIZED"


@pytest.mark.parametrize(
    ("updates", "reason", "expected_disposition"),
    [
        ({"transmitter_attested": False}, "TRANSMITTER_NOT_ATTESTED", PBAState.FAULT_LATCHED),
        ({"receiver_attested": False}, "RECEIVER_NOT_ATTESTED", PBAState.FAULT_LATCHED),
        ({"telemetry_fresh": False}, "TELEMETRY_STALE", PBAState.RAMP_DOWN),
        ({"tracking_valid": False}, "TRACKING_INVALID", PBAState.RAMP_DOWN),
        ({"navigation_valid": False}, "NAVIGATION_INVALID", PBAState.RAMP_DOWN),
        ({"critical_state_disagreement": True}, "CRITICAL_STATE_DISAGREEMENT", PBAState.RAMP_DOWN),
        ({"configuration_changed": True}, "CONFIGURATION_CHANGED", PBAState.FAULT_LATCHED),
        ({"identity_changed": True}, "IDENTITY_CHANGED", PBAState.FAULT_LATCHED),
        ({"safety_veto": True}, "SAFETY_VETO", PBAState.FAULT_LATCHED),
    ],
)
def test_faults_fail_closed(
    updates: dict[str, object], reason: str, expected_disposition: PBAState
) -> None:
    now = datetime.now(timezone.utc)
    observed = observation(**updates)
    decision = evaluate_delivery_authorization(token(now), observed, now=now)
    assert decision.permitted is False
    assert decision.reason == reason
    assert fault_disposition(observed) is expected_disposition


def test_wrong_receiver_is_denied() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_delivery_authorization(
        token(now), observation(receiver_id="rx-other"), now=now
    )
    assert decision.permitted is False
    assert decision.reason == "RECEIVER_ID_MISMATCH"


def test_configuration_digest_mismatch_is_denied() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_delivery_authorization(
        token(now), observation(configuration_digest=D4), now=now
    )
    assert decision.permitted is False
    assert decision.reason == "CONFIGURATION_DIGEST_MISMATCH"


def test_expired_authorization_is_denied() -> None:
    issued = datetime.now(timezone.utc) - timedelta(hours=1)
    decision = evaluate_delivery_authorization(
        token(issued), observation(), now=datetime.now(timezone.utc)
    )
    assert decision.permitted is False
    assert decision.reason == "AUTHORIZATION_OUTSIDE_VALIDITY_WINDOW"


def make_event(sequence: int, previous_event_hash: str) -> PBAEvidenceEvent:
    return seal_event(
        PBAEvidenceEvent(
            event_id=uuid4(),
            mission_id="PBA-G1-TEST",
            sequence=sequence,
            timestamp=datetime.now(timezone.utc),
            prior_state=PBAState.VERIFY_ONLY,
            requested_state=PBAState.DELIVERY_AUTHORIZED,
            resulting_state=PBAState.DELIVERY_AUTHORIZED,
            authorization_id=uuid4(),
            permitted=True,
            rule="PBA-I01-I08",
            reason="DELIVERY_AUTHORIZED",
            identity_digest=D0,
            configuration_digest=D1,
            navigation_digest=D2,
            tracking_digest=D3,
            interlock_digest=D4,
            previous_event_hash=previous_event_hash,
            event_hash=D0,
        )
    )


def test_evidence_chain_detects_tampering_and_sequence_breaks() -> None:
    first = make_event(10, GENESIS_HASH)
    second = make_event(11, first.event_hash)
    assert verify_chain([first, second])

    tampered = second.model_copy(update={"reason": "ALTERED"})
    assert not verify_chain([first, tampered])

    skipped = make_event(13, first.event_hash)
    assert not verify_chain([first, skipped])

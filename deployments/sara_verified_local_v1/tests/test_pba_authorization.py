from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.pba_adapter import PBAAdapterEnvelope, PBAPartnerAdapter
from worldshepherd_sara.pba_authorization import (
    PBAAuthorizationError,
    PBAAuthorizationVerifier,
    PBAReplayError,
    PBAReplayLedger,
    canonical_pba_authorization_message,
    verify_and_claim,
)
from worldshepherd_sara.pba_gate import authorize_delivery_once
from worldshepherd_sara.pba_models import (
    OperatingState,
    PBAObservation,
    SafeToBeamAuthorization,
)


D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def key_material() -> tuple[Ed25519PrivateKey, str]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private, _b64url(public)


def resign(
    private: Ed25519PrivateKey, token: SafeToBeamAuthorization
) -> SafeToBeamAuthorization:
    unsigned = token.model_copy(update={"signature": "placeholder"})
    signature = private.sign(canonical_pba_authorization_message(unsigned))
    return unsigned.model_copy(update={"signature": _b64url(signature)})


def signed_token(
    private: Ed25519PrivateKey,
    *,
    key_id: str = "pba-test-key",
    now: datetime | None = None,
    sequence: int = 1,
    nonce: str | None = None,
    authorization_id=None,
    receiver_id: str = "rx-001",
    mission_id: str = "PBA-G2-TEST",
) -> SafeToBeamAuthorization:
    now = now or datetime.now(timezone.utc)
    unsigned = SafeToBeamAuthorization(
        authorization_id=authorization_id or uuid4(),
        mission_id=mission_id,
        transmitter_id="tx-001",
        receiver_id=receiver_id,
        transmitter_attestation="attest-tx",
        receiver_attestation="attest-rx",
        configuration_digest=D1,
        navigation_digest=D2,
        tracking_digest=D3,
        valid_from=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=5),
        allowed_state=OperatingState.DELIVERY_AUTHORIZED,
        policy_id="PBA-TEST-02",
        authority_id="PRIME-TEST",
        key_id=key_id,
        previous_event_hash=D0,
        nonce=nonce or f"nonce-{uuid4().hex}",
        sequence=sequence,
        signature="placeholder",
    )
    return resign(private, unsigned)


def verifier(public_key_b64url: str, *, revoked: set[str] | None = None) -> PBAAuthorizationVerifier:
    return PBAAuthorizationVerifier(
        public_keys_b64url={"pba-test-key": public_key_b64url},
        revoked_key_ids=revoked,
    )


def observation() -> PBAObservation:
    return PBAObservation(
        transmitter_id="tx-001",
        receiver_id="rx-001",
        configuration_digest=D1,
        navigation_digest=D2,
        tracking_digest=D3,
        transmitter_attested=True,
        receiver_attested=True,
        navigation_valid=True,
        tracking_valid=True,
        telemetry_fresh=True,
    )


def test_valid_signature_verifies_and_persists_replay_claim(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now, sequence=1)
    ledger_path = tmp_path / "pba-replay.sqlite3"

    verified = verify_and_claim(
        verifier(public), PBAReplayLedger(ledger_path), token, now=now
    )
    assert verified.authorization_id == str(token.authorization_id)
    assert verified.sequence == 1

    restarted = PBAReplayLedger(ledger_path)
    with pytest.raises(PBAReplayError, match="authorization_id"):
        restarted.claim(verified)


def test_signature_tamper_is_rejected() -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now)
    tampered = token.model_copy(update={"receiver_id": "rx-other"})

    with pytest.raises(PBAAuthorizationError, match="invalid WS-PBA Ed25519 signature"):
        verifier(public).verify(tampered, now=now)


def test_malformed_signature_length_is_rejected() -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now).model_copy(update={"signature": "AA"})

    with pytest.raises(PBAAuthorizationError, match="must decode to 64 bytes"):
        verifier(public).verify(token, now=now)


def test_unknown_and_revoked_keys_fail_closed() -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now)

    with pytest.raises(PBAAuthorizationError, match="unknown WS-PBA signing key"):
        PBAAuthorizationVerifier(public_keys_b64url={"other": public}).verify(token, now=now)

    with pytest.raises(PBAAuthorizationError, match="revoked"):
        verifier(public, revoked={"pba-test-key"}).verify(token, now=now)


def test_missing_g2_key_metadata_is_rejected() -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now).model_copy(update={"key_id": None})

    with pytest.raises(PBAAuthorizationError, match="no signer key_id"):
        verifier(public).verify(token, now=now)


def test_naive_verification_clock_is_rejected() -> None:
    private, public = key_material()
    aware_now = datetime.now(timezone.utc)
    token = signed_token(private, now=aware_now)

    with pytest.raises(PBAAuthorizationError, match="timezone-aware"):
        verifier(public).verify(token, now=datetime.now())


def test_excessive_authorization_lifetime_is_rejected() -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now)
    overlong = token.model_copy(
        update={
            "valid_from": now - timedelta(seconds=5),
            "valid_until": now + timedelta(minutes=16),
        }
    )
    overlong = resign(private, overlong)

    with pytest.raises(PBAAuthorizationError, match="lifetime exceeds policy"):
        verifier(public).verify(overlong, now=now)


def test_duplicate_authorization_id_is_rejected(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    shared_id = uuid4()
    first = signed_token(private, now=now, sequence=1, authorization_id=shared_id)
    second = signed_token(private, now=now, sequence=2, authorization_id=shared_id)
    ledger = PBAReplayLedger(tmp_path / "pba-replay.sqlite3")
    auth_verifier = verifier(public)

    ledger.claim(auth_verifier.verify(first, now=now))
    with pytest.raises(PBAReplayError, match="authorization_id"):
        ledger.claim(auth_verifier.verify(second, now=now))


def test_duplicate_nonce_is_rejected(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    shared_nonce = f"nonce-{uuid4().hex}"
    first = signed_token(private, now=now, sequence=1, nonce=shared_nonce)
    second = signed_token(private, now=now, sequence=2, nonce=shared_nonce)
    ledger = PBAReplayLedger(tmp_path / "pba-replay.sqlite3")
    auth_verifier = verifier(public)

    ledger.claim(auth_verifier.verify(first, now=now))
    with pytest.raises(PBAReplayError, match="nonce"):
        ledger.claim(auth_verifier.verify(second, now=now))


def test_nonmonotonic_sequence_is_rejected_across_restart(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    ledger_path = tmp_path / "pba-replay.sqlite3"
    auth_verifier = verifier(public)

    first = signed_token(private, now=now, sequence=5)
    PBAReplayLedger(ledger_path).claim(auth_verifier.verify(first, now=now))

    stale = signed_token(private, now=now, sequence=4)
    with pytest.raises(PBAReplayError, match="strictly monotonic"):
        PBAReplayLedger(ledger_path).claim(auth_verifier.verify(stale, now=now))

    fresh = signed_token(private, now=now, sequence=6)
    PBAReplayLedger(ledger_path).claim(auth_verifier.verify(fresh, now=now))


def test_sequence_scope_is_per_mission_and_endpoint_pair(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    ledger = PBAReplayLedger(tmp_path / "pba-replay.sqlite3")
    auth_verifier = verifier(public)

    first = signed_token(private, now=now, sequence=7, receiver_id="rx-001")
    second = signed_token(private, now=now, sequence=7, receiver_id="rx-002")
    third = signed_token(
        private,
        now=now,
        sequence=7,
        receiver_id="rx-001",
        mission_id="PBA-G2-OTHER",
    )

    ledger.claim(auth_verifier.verify(first, now=now))
    ledger.claim(auth_verifier.verify(second, now=now))
    ledger.claim(auth_verifier.verify(third, now=now))


def test_expired_and_far_future_tokens_fail_closed() -> None:
    private, public = key_material()
    current = datetime.now(timezone.utc)
    auth_verifier = verifier(public)

    expired = signed_token(private, now=current - timedelta(hours=1))
    with pytest.raises(PBAAuthorizationError, match="expired"):
        auth_verifier.verify(expired, now=current)

    future = signed_token(private, now=current + timedelta(minutes=5))
    with pytest.raises(PBAAuthorizationError, match="too far in the future"):
        auth_verifier.verify(future, now=current)


def test_combined_gate_does_not_burn_token_on_transient_semantic_denial(tmp_path) -> None:
    private, public = key_material()
    now = datetime.now(timezone.utc)
    token = signed_token(private, now=now, sequence=9)
    ledger = PBAReplayLedger(tmp_path / "pba-replay.sqlite3")
    auth_verifier = verifier(public)

    stale = observation().model_copy(update={"telemetry_fresh": False})
    denied = authorize_delivery_once(
        verifier=auth_verifier,
        ledger=ledger,
        token=token,
        observation=stale,
        now=now,
    )
    assert denied.permitted is False
    assert denied.reason == "TELEMETRY_STALE"

    permitted = authorize_delivery_once(
        verifier=auth_verifier,
        ledger=ledger,
        token=token,
        observation=observation(),
        now=now,
    )
    assert permitted.permitted is True
    assert permitted.reason == "DELIVERY_AUTHORIZED"

    with pytest.raises(PBAReplayError, match="authorization_id"):
        authorize_delivery_once(
            verifier=auth_verifier,
            ledger=ledger,
            token=token,
            observation=observation(),
            now=now,
        )


def test_adapter_contract_is_read_only_snapshot_boundary() -> None:
    class SyntheticAdapter:
        adapter_id = "synthetic-g2"

        def snapshot(self) -> PBAAdapterEnvelope:
            return PBAAdapterEnvelope(
                adapter_id=self.adapter_id,
                observed_at=datetime.now(timezone.utc),
                observation=observation(),
            )

    adapter = SyntheticAdapter()
    assert isinstance(adapter, PBAPartnerAdapter)
    envelope = adapter.snapshot()
    assert envelope.adapter_id == "synthetic-g2"
    assert envelope.observation.telemetry_fresh is True

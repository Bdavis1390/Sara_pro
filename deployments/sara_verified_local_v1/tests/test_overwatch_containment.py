from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_sara.overwatch_containment import (
    OVERWATCH_CONTAINMENT_REGISTRY_KEY,
    OverwatchContainmentDirective,
    OverwatchContainmentError,
    OverwatchContainmentState,
    OverwatchContainmentVerifier,
    OverwatchDirectiveSignature,
    canonical_overwatch_message,
    evaluate_overwatch_containment,
    verified_containment_registry_patch,
)
from worldshepherd_sara.prime_configuration_custody import PrimeEnvironment


NOW = datetime(2026, 9, 17, 19, 0, tzinfo=timezone.utc)


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _keys():
    private_a = Ed25519PrivateKey.generate()
    private_b = Ed25519PrivateKey.generate()
    private_c = Ed25519PrivateKey.generate()
    verifier = OverwatchContainmentVerifier(
        public_keys_b64url={
            "OW-A": _b64url(private_a.public_key().public_bytes_raw()),
            "OW-B": _b64url(private_b.public_key().public_bytes_raw()),
            "OW-C": _b64url(private_c.public_key().public_bytes_raw()),
        },
        hold_quorum=1,
        clear_quorum=2,
    )
    return {"OW-A": private_a, "OW-B": private_b, "OW-C": private_c}, verifier


def _directive(
    keys: dict[str, Ed25519PrivateKey],
    *,
    state: OverwatchContainmentState,
    signer_ids: tuple[str, ...],
    sequence: int = 1,
    previous: str | None = None,
    directive_id: str | None = None,
    reason_code: str | None = None,
    prime_id: str = "PRIME-OW-1",
    target_environment: PrimeEnvironment = PrimeEnvironment.SPACE,
) -> OverwatchContainmentDirective:
    placeholders = [
        OverwatchDirectiveSignature(key_id=key_id, signature_b64url="placeholder")
        for key_id in signer_ids
    ]
    directive = OverwatchContainmentDirective(
        directive_id=directive_id or f"OW-{state.value}-{sequence}",
        prime_id=prime_id,
        target_environment=target_environment,
        state=state,
        sequence=sequence,
        previous_directive_sha256=previous,
        reason_code=reason_code or ("ANOMALY.HOLD" if state == OverwatchContainmentState.HOLD else "AUTHORIZED.CLEAR"),
        issued_at=NOW - timedelta(seconds=10),
        expires_at=NOW + timedelta(minutes=5),
        nonce=f"overwatch-nonce-{state.value.lower()}-{sequence:04d}",
        signatures=placeholders,
    )
    message = canonical_overwatch_message(directive)
    signatures = [
        OverwatchDirectiveSignature(
            key_id=key_id,
            signature_b64url=_b64url(keys[key_id].sign(message)),
        )
        for key_id in signer_ids
    ]
    return directive.model_copy(update={"signatures": signatures})


def test_single_signed_hold_is_verified_and_active():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    patch = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)
    registry = dict(patch)

    status = evaluate_overwatch_containment(
        registry,
        prime_id="PRIME-OW-1",
        action="REQUALIFICATION_RELEASE",
        target_environment=PrimeEnvironment.SPACE,
        verifier=verifier,
        now=NOW,
    )

    assert status.active is True
    assert status.state == OverwatchContainmentState.HOLD
    assert status.sequence == 1
    assert status.directive_id == hold.directive_id
    assert status.directive_sha256
    assert status.signer_key_ids == ["OW-A"]


def test_clear_requires_two_distinct_valid_signers_and_predecessor_binding():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    registry = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)
    hold_hash = registry[OVERWATCH_CONTAINMENT_REGISTRY_KEY]["PRIME-OW-1"]["directive_sha256"]

    insufficient_clear = _directive(
        keys,
        state=OverwatchContainmentState.CLEAR,
        signer_ids=("OW-B",),
        sequence=2,
        previous=hold_hash,
    )
    with pytest.raises(OverwatchContainmentError, match="requires 2 distinct signatures"):
        verified_containment_registry_patch(
            registry,
            insufficient_clear,
            verifier=verifier,
            now=NOW,
        )

    clear = _directive(
        keys,
        state=OverwatchContainmentState.CLEAR,
        signer_ids=("OW-B", "OW-C"),
        sequence=2,
        previous=hold_hash,
    )
    registry.update(
        verified_containment_registry_patch(registry, clear, verifier=verifier, now=NOW)
    )
    status = evaluate_overwatch_containment(
        registry,
        prime_id="PRIME-OW-1",
        action="REQUALIFICATION_RELEASE",
        target_environment=PrimeEnvironment.SPACE,
        verifier=verifier,
        now=NOW,
    )
    assert status.active is False
    assert status.state == OverwatchContainmentState.CLEAR
    assert status.sequence == 2
    assert status.signer_key_ids == ["OW-B", "OW-C"]


def test_stale_replay_and_predecessor_substitution_fail_closed():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    registry = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)

    with pytest.raises(OverwatchContainmentError, match="sequence"):
        verified_containment_registry_patch(registry, hold, verifier=verifier, now=NOW)

    wrong_previous = "0" * 64
    clear = _directive(
        keys,
        state=OverwatchContainmentState.CLEAR,
        signer_ids=("OW-B", "OW-C"),
        sequence=2,
        previous=wrong_previous,
    )
    with pytest.raises(OverwatchContainmentError, match="predecessor"):
        verified_containment_registry_patch(registry, clear, verifier=verifier, now=NOW)


def test_stored_directive_tamper_is_detected_during_gate_evaluation():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    registry = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)
    record = registry[OVERWATCH_CONTAINMENT_REGISTRY_KEY]["PRIME-OW-1"]
    record["directive"]["reason_code"] = "TAMPERED.HOLD"

    with pytest.raises(OverwatchContainmentError, match="signature"):
        evaluate_overwatch_containment(
            registry,
            prime_id="PRIME-OW-1",
            action="REQUALIFICATION_RELEASE",
            target_environment=PrimeEnvironment.SPACE,
            verifier=verifier,
            now=NOW,
        )


def test_persisted_containment_requires_verifier_in_consequential_path():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    registry = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)

    with pytest.raises(OverwatchContainmentError, match="verifier is required"):
        evaluate_overwatch_containment(
            registry,
            prime_id="PRIME-OW-1",
            action="REQUALIFICATION_RELEASE",
            target_environment=PrimeEnvironment.SPACE,
            verifier=None,
            now=NOW,
        )


def test_revoked_hold_signing_key_causes_fail_closed_revalidation():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )
    registry = verified_containment_registry_patch({}, hold, verifier=verifier, now=NOW)
    revoked = OverwatchContainmentVerifier(
        public_keys_b64url={
            key_id: _b64url(private.public_key().public_bytes_raw())
            for key_id, private in keys.items()
        },
        revoked_key_ids={"OW-A"},
        hold_quorum=1,
        clear_quorum=2,
    )

    with pytest.raises(OverwatchContainmentError, match="revoked"):
        evaluate_overwatch_containment(
            registry,
            prime_id="PRIME-OW-1",
            action="REQUALIFICATION_RELEASE",
            target_environment=PrimeEnvironment.SPACE,
            verifier=revoked,
            now=NOW,
        )


def test_expired_unapplied_directive_cannot_be_introduced():
    keys, verifier = _keys()
    hold = _directive(
        keys,
        state=OverwatchContainmentState.HOLD,
        signer_ids=("OW-A",),
    )

    with pytest.raises(OverwatchContainmentError, match="issuance window is expired"):
        verified_containment_registry_patch(
            {},
            hold,
            verifier=verifier,
            now=NOW + timedelta(minutes=10),
        )

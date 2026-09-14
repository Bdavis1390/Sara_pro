from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .sovereign_boundary_authority import VerifiedPrimeEffectAuthorization
from .sovereign_boundary_kernel import SovereignBoundaryEnvelope, verify_boundary_envelope


PRIME_EFFECT_AUTHZ_LEDGER_KEY = "PRIME_SENTINEL_EFFECT_AUTHORIZATIONS"
_VALID_STATUSES = frozenset(
    {"VERIFIED", "CLAIMED", "INVOKING", "CONSUMED", "INDETERMINATE"}
)


class PrimeEffectAuthorizationLedgerError(ValueError):
    pass


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ledger(registry: dict[str, Any]) -> dict[str, Any]:
    raw = registry.get(PRIME_EFFECT_AUTHZ_LEDGER_KEY, {})
    if not isinstance(raw, dict):
        raise PrimeEffectAuthorizationLedgerError(
            f"{PRIME_EFFECT_AUTHZ_LEDGER_KEY} must be a JSON object"
        )
    return dict(raw)


def _validate_entry(authorization_id: str, entry: Any) -> None:
    if not isinstance(entry, dict):
        raise PrimeEffectAuthorizationLedgerError(
            "effect-authorization ledger entry is malformed"
        )
    if entry.get("authorization_id") != authorization_id:
        raise PrimeEffectAuthorizationLedgerError(
            "effect-authorization ledger ID mismatch"
        )
    if entry.get("status") not in _VALID_STATUSES:
        raise PrimeEffectAuthorizationLedgerError(
            "effect-authorization ledger status is invalid"
        )


def _authorization_expiry(entry: dict[str, Any]) -> datetime:
    try:
        expires = datetime.fromisoformat(str(entry["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise PrimeEffectAuthorizationLedgerError(
            "recorded authorization expiry is invalid"
        ) from exc
    if expires.tzinfo is None:
        raise PrimeEffectAuthorizationLedgerError(
            "recorded authorization expiry must be timezone-aware"
        )
    return expires.astimezone(timezone.utc)


def _assert_envelope_binding(
    entry: dict[str, Any],
    *,
    authorization_id: str,
    envelope: SovereignBoundaryEnvelope,
    execution_id: str,
) -> None:
    if entry.get("execution_id") != execution_id:
        raise PrimeEffectAuthorizationLedgerError("execution claim ID mismatch")
    if entry.get("envelope_id") != envelope.envelope_id:
        raise PrimeEffectAuthorizationLedgerError("execution claim envelope mismatch")
    if entry.get("action_digest") != envelope.action_digest:
        raise PrimeEffectAuthorizationLedgerError("execution claim action mismatch")
    if envelope.prime_authorization_ref != authorization_id:
        raise PrimeEffectAuthorizationLedgerError(
            "envelope authorization reference mismatch"
        )
    if envelope.prime_execution_claim_ref != execution_id:
        raise PrimeEffectAuthorizationLedgerError(
            "envelope execution claim reference mismatch"
        )


def verified_effect_authorization_registry_patch(
    registry: dict[str, Any],
    verified: VerifiedPrimeEffectAuthorization,
) -> dict[str, Any]:
    records = _ledger(registry)
    if verified.authorization_id in records:
        raise PrimeEffectAuthorizationLedgerError(
            "authorization_id has already been recorded"
        )
    for authorization_id, entry in records.items():
        _validate_entry(authorization_id, entry)
        if entry.get("nonce") == verified.nonce:
            raise PrimeEffectAuthorizationLedgerError(
                "authorization nonce has already been recorded"
            )

    records[verified.authorization_id] = {
        "authorization_id": verified.authorization_id,
        "status": "VERIFIED",
        "envelope_id": verified.envelope_id,
        "actor": verified.actor,
        "action_digest": verified.action_digest,
        "effect_scope": verified.effect_scope.value,
        "capability_status": verified.capability_status.value,
        "policy_revision": verified.policy_revision,
        "human_approval_ref": verified.human_approval_ref,
        "key_id": verified.key_id,
        "key_fingerprint_sha256": verified.key_fingerprint_sha256,
        "nonce": verified.nonce,
        "issued_at": _utc_iso(verified.issued_at),
        "expires_at": _utc_iso(verified.expires_at),
    }
    return {PRIME_EFFECT_AUTHZ_LEDGER_KEY: records}


def claim_effect_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    envelope: SovereignBoundaryEnvelope,
    execution_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not verify_boundary_envelope(envelope):
        raise PrimeEffectAuthorizationLedgerError(
            "cannot claim against an unverified SBK envelope"
        )
    if envelope.prime_authorization_ref != authorization_id:
        raise PrimeEffectAuthorizationLedgerError(
            "envelope PRIME authorization reference mismatch"
        )
    if not execution_id:
        raise PrimeEffectAuthorizationLedgerError("execution_id must be non-empty")

    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] != "VERIFIED":
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization is not claimable"
        )

    expected = {
        "envelope_id": envelope.envelope_id,
        "actor": envelope.actor,
        "action_digest": envelope.action_digest,
        "effect_scope": envelope.action.effect_scope.value,
        "capability_status": envelope.action.capability_status.value,
        "policy_revision": envelope.policy.policy_revision,
        "human_approval_ref": envelope.human_approval_ref,
        "key_fingerprint_sha256": envelope.prime_authorization_key_fingerprint_sha256,
    }
    mismatches = [name for name, value in expected.items() if entry.get(name) != value]
    if mismatches:
        raise PrimeEffectAuthorizationLedgerError(
            "recorded effect authorization does not bind current envelope: "
            + ", ".join(sorted(mismatches))
        )

    current = (now or _utc_now()).astimezone(timezone.utc)
    if current >= _authorization_expiry(entry):
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization expired before claim"
        )

    updated = dict(entry)
    updated.update(
        {
            "status": "CLAIMED",
            "execution_id": execution_id,
            "claimed_at": _utc_iso(current),
        }
    )
    records[authorization_id] = updated
    return {PRIME_EFFECT_AUTHZ_LEDGER_KEY: records}


def assert_claimed_effect_authorization_usable(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    envelope: SovereignBoundaryEnvelope,
    execution_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] != "CLAIMED":
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization is not in CLAIMED state"
        )
    _assert_envelope_binding(
        entry,
        authorization_id=authorization_id,
        envelope=envelope,
        execution_id=execution_id,
    )
    current = (now or _utc_now()).astimezone(timezone.utc)
    if current >= _authorization_expiry(entry):
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization expired before invocation"
        )
    return dict(entry)


def begin_effect_invocation_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    envelope: SovereignBoundaryEnvelope,
    execution_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Persist the one-way execution fence before any physical executor is called.

    Only one caller can transition a durable authorization from CLAIMED to
    INVOKING under ``DurableStore.transact_registry``. A second caller sees
    INVOKING and must fail before invoking an external side effect. If the
    process dies after this fence is persisted, operators must treat the effect
    as potentially invoked and reconcile it rather than replaying the claim.
    """

    if not verify_boundary_envelope(envelope):
        raise PrimeEffectAuthorizationLedgerError(
            "cannot begin invocation for an unverified SBK envelope"
        )

    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] != "CLAIMED":
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization is not in CLAIMED state"
        )
    _assert_envelope_binding(
        entry,
        authorization_id=authorization_id,
        envelope=envelope,
        execution_id=execution_id,
    )

    current = (now or _utc_now()).astimezone(timezone.utc)
    if current >= _authorization_expiry(entry):
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization expired before invocation"
        )

    updated = dict(entry)
    updated.update(
        {
            "status": "INVOKING",
            "invocation_started_at": _utc_iso(current),
        }
    )
    records[authorization_id] = updated
    return {PRIME_EFFECT_AUTHZ_LEDGER_KEY: records}


def assert_invoking_effect_authorization_usable(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    envelope: SovereignBoundaryEnvelope,
    execution_id: str,
) -> dict[str, Any]:
    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] != "INVOKING":
        raise PrimeEffectAuthorizationLedgerError(
            "effect authorization is not in INVOKING state"
        )
    _assert_envelope_binding(
        entry,
        authorization_id=authorization_id,
        envelope=envelope,
        execution_id=execution_id,
    )
    return dict(entry)


def consumed_effect_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    execution_id: str,
    terminal_envelope: SovereignBoundaryEnvelope,
    consumed_at: datetime | None = None,
) -> dict[str, Any]:
    if not verify_boundary_envelope(terminal_envelope):
        raise PrimeEffectAuthorizationLedgerError(
            "terminal SBK envelope failed digest verification"
        )
    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] != "INVOKING":
        raise PrimeEffectAuthorizationLedgerError(
            "only an INVOKING authorization can be consumed"
        )
    _assert_envelope_binding(
        entry,
        authorization_id=authorization_id,
        envelope=terminal_envelope,
        execution_id=execution_id,
    )

    updated = dict(entry)
    updated.update(
        {
            "status": "CONSUMED",
            "terminal_state": terminal_envelope.state.value,
            "terminal_envelope_digest": terminal_envelope.envelope_digest,
            "consumed_at": _utc_iso(consumed_at or _utc_now()),
        }
    )
    records[authorization_id] = updated
    return {PRIME_EFFECT_AUTHZ_LEDGER_KEY: records}


def indeterminate_effect_authorization_registry_patch(
    registry: dict[str, Any],
    *,
    authorization_id: str,
    execution_id: str,
    reason: str,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Fail closed when the caller cannot prove whether a claimed effect occurred.

    INDETERMINATE authorizations are never automatically reusable. Human review
    must create a fresh authorization rather than retrying the same claim.
    ``CLAIMED`` is accepted for conservative recovery when a caller cannot prove
    whether invocation began; normal physical PEP failures occur from INVOKING.
    """

    if not reason:
        raise PrimeEffectAuthorizationLedgerError(
            "indeterminate state requires a reason"
        )
    records = _ledger(registry)
    entry = records.get(authorization_id)
    _validate_entry(authorization_id, entry)
    assert isinstance(entry, dict)
    if entry["status"] not in {"CLAIMED", "INVOKING"}:
        raise PrimeEffectAuthorizationLedgerError(
            "only the matching CLAIMED or INVOKING authorization can become indeterminate"
        )
    if entry.get("execution_id") != execution_id:
        raise PrimeEffectAuthorizationLedgerError("execution claim ID mismatch")
    updated = dict(entry)
    updated.update(
        {
            "status": "INDETERMINATE",
            "indeterminate_reason": reason,
            "indeterminate_at": _utc_iso(observed_at or _utc_now()),
        }
    )
    records[authorization_id] = updated
    return {PRIME_EFFECT_AUTHZ_LEDGER_KEY: records}

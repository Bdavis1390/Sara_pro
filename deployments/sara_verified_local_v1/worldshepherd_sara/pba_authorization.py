from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field

from .pba_models import SafeToBeamAuthorization


MAX_AUTHORIZATION_LIFETIME = timedelta(minutes=15)
MAX_FUTURE_SKEW = timedelta(seconds=60)


class PBAAuthorizationError(ValueError):
    pass


class PBAReplayError(PBAAuthorizationError):
    pass


class VerifiedPBAAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    authorization_id: str
    mission_id: str
    transmitter_id: str
    receiver_id: str
    key_id: str
    key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    nonce: str
    sequence: int = Field(ge=0)
    valid_from: datetime
    valid_until: datetime


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_pba_authorization_message(token: SafeToBeamAuthorization) -> bytes:
    """Return the exact G2 signature input for a WS-PBA authorization token."""

    if not token.key_id:
        raise PBAAuthorizationError("WS-PBA authorization has no signer key_id")

    payload: dict[str, Any] = {
        "schema_version": token.schema_version,
        "authorization_id": str(token.authorization_id),
        "mission_id": token.mission_id,
        "transmitter_id": token.transmitter_id,
        "receiver_id": token.receiver_id,
        "transmitter_attestation": token.transmitter_attestation,
        "receiver_attestation": token.receiver_attestation,
        "configuration_digest": token.configuration_digest,
        "navigation_digest": token.navigation_digest,
        "tracking_digest": token.tracking_digest,
        "valid_from": _utc_iso(token.valid_from),
        "valid_until": _utc_iso(token.valid_until),
        "allowed_state": token.allowed_state.value,
        "policy_id": token.policy_id,
        "authority_id": token.authority_id,
        "key_id": token.key_id,
        "previous_event_hash": token.previous_event_hash,
        "nonce": token.nonce,
        "sequence": token.sequence,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return b"WS-PBA-AUTHORIZATION-V0.3\0" + encoded


def _decode_b64url(value: str, *, expected_length: int, label: str) -> bytes:
    try:
        encoded = value.encode("ascii")
        padded = encoded + b"=" * (-len(encoded) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
        raise PBAAuthorizationError(f"invalid {label} encoding") from exc
    if len(decoded) != expected_length:
        raise PBAAuthorizationError(f"{label} must decode to {expected_length} bytes")
    return decoded


class PBAAuthorizationVerifier:
    """Verification-only Ed25519 trust boundary for WS-PBA authorizations."""

    def __init__(
        self,
        *,
        public_keys_b64url: dict[str, str],
        revoked_key_ids: set[str] | None = None,
        max_lifetime: timedelta = MAX_AUTHORIZATION_LIFETIME,
        max_future_skew: timedelta = MAX_FUTURE_SKEW,
    ) -> None:
        if max_lifetime <= timedelta(0):
            raise ValueError("max_lifetime must be positive")
        if max_future_skew < timedelta(0):
            raise ValueError("max_future_skew must be non-negative")

        self._public_keys: dict[str, bytes] = {}
        for key_id, encoded in public_keys_b64url.items():
            if not key_id:
                raise ValueError("WS-PBA key id cannot be empty")
            self._public_keys[key_id] = _decode_b64url(
                encoded, expected_length=32, label=f"public key {key_id}"
            )
        self.revoked_key_ids = frozenset(revoked_key_ids or set())
        self.max_lifetime = max_lifetime
        self.max_future_skew = max_future_skew

    @property
    def configured(self) -> bool:
        return bool(self._public_keys)

    def _key_bytes(self, key_id: str | None) -> bytes:
        if not key_id:
            raise PBAAuthorizationError("WS-PBA authorization has no signer key_id")
        if not self.configured:
            raise PBAAuthorizationError("no WS-PBA public keys are configured")
        if key_id in self.revoked_key_ids:
            raise PBAAuthorizationError("WS-PBA signing key is revoked")
        key_bytes = self._public_keys.get(key_id)
        if key_bytes is None:
            raise PBAAuthorizationError("unknown WS-PBA signing key")
        return key_bytes

    def verify(
        self,
        token: SafeToBeamAuthorization,
        *,
        now: datetime | None = None,
    ) -> VerifiedPBAAuthorization:
        key_bytes = self._key_bytes(token.key_id)

        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        valid_from = token.valid_from.astimezone(timezone.utc)
        valid_until = token.valid_until.astimezone(timezone.utc)

        if valid_until - valid_from > self.max_lifetime:
            raise PBAAuthorizationError("WS-PBA authorization lifetime exceeds policy")
        if valid_from > current + self.max_future_skew:
            raise PBAAuthorizationError("WS-PBA authorization begins too far in the future")
        if current < valid_from:
            raise PBAAuthorizationError("WS-PBA authorization is not yet valid")
        if current >= valid_until:
            raise PBAAuthorizationError("WS-PBA authorization is expired")

        signature = _decode_b64url(
            token.signature,
            expected_length=64,
            label="Ed25519 signature",
        )
        try:
            Ed25519PublicKey.from_public_bytes(key_bytes).verify(
                signature,
                canonical_pba_authorization_message(token),
            )
        except (InvalidSignature, ValueError) as exc:
            raise PBAAuthorizationError("invalid WS-PBA Ed25519 signature") from exc

        return VerifiedPBAAuthorization(
            authorization_id=str(token.authorization_id),
            mission_id=token.mission_id,
            transmitter_id=token.transmitter_id,
            receiver_id=token.receiver_id,
            key_id=token.key_id,
            key_fingerprint_sha256=hashlib.sha256(key_bytes).hexdigest(),
            nonce=token.nonce,
            sequence=token.sequence,
            valid_from=valid_from,
            valid_until=valid_until,
        )


class PBAReplayLedger:
    """Crash-persistent replay and monotonic-sequence guard for verified tokens."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS pba_authorization_claims (
                    authorization_id TEXT PRIMARY KEY,
                    nonce TEXT NOT NULL UNIQUE,
                    mission_id TEXT NOT NULL,
                    transmitter_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL CHECK(sequence >= 0),
                    key_id TEXT NOT NULL,
                    key_fingerprint_sha256 TEXT NOT NULL,
                    valid_from TEXT NOT NULL,
                    valid_until TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS pba_sequence_state (
                    mission_id TEXT NOT NULL,
                    transmitter_id TEXT NOT NULL,
                    receiver_id TEXT NOT NULL,
                    highest_sequence INTEGER NOT NULL CHECK(highest_sequence >= 0),
                    PRIMARY KEY (mission_id, transmitter_id, receiver_id)
                );
                """
            )
        finally:
            connection.close()

    def claim(self, verified: VerifiedPBAAuthorization) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")

            if connection.execute(
                "SELECT 1 FROM pba_authorization_claims WHERE authorization_id = ?",
                (verified.authorization_id,),
            ).fetchone():
                raise PBAReplayError("authorization_id has already been claimed")

            if connection.execute(
                "SELECT 1 FROM pba_authorization_claims WHERE nonce = ?",
                (verified.nonce,),
            ).fetchone():
                raise PBAReplayError("authorization nonce has already been claimed")

            row = connection.execute(
                """
                SELECT highest_sequence
                FROM pba_sequence_state
                WHERE mission_id = ? AND transmitter_id = ? AND receiver_id = ?
                """,
                (
                    verified.mission_id,
                    verified.transmitter_id,
                    verified.receiver_id,
                ),
            ).fetchone()
            if row is not None and verified.sequence <= int(row["highest_sequence"]):
                raise PBAReplayError("authorization sequence is not strictly monotonic")

            connection.execute(
                """
                INSERT INTO pba_authorization_claims (
                    authorization_id, nonce, mission_id, transmitter_id, receiver_id,
                    sequence, key_id, key_fingerprint_sha256, valid_from, valid_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verified.authorization_id,
                    verified.nonce,
                    verified.mission_id,
                    verified.transmitter_id,
                    verified.receiver_id,
                    verified.sequence,
                    verified.key_id,
                    verified.key_fingerprint_sha256,
                    _utc_iso(verified.valid_from),
                    _utc_iso(verified.valid_until),
                ),
            )
            connection.execute(
                """
                INSERT INTO pba_sequence_state (
                    mission_id, transmitter_id, receiver_id, highest_sequence
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(mission_id, transmitter_id, receiver_id)
                DO UPDATE SET highest_sequence = excluded.highest_sequence
                """,
                (
                    verified.mission_id,
                    verified.transmitter_id,
                    verified.receiver_id,
                    verified.sequence,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def verify_and_claim(
    verifier: PBAAuthorizationVerifier,
    ledger: PBAReplayLedger,
    token: SafeToBeamAuthorization,
    *,
    now: datetime | None = None,
) -> VerifiedPBAAuthorization:
    verified = verifier.verify(token, now=now)
    ledger.claim(verified)
    return verified

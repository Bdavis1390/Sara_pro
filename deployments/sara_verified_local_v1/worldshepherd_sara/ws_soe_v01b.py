"""WS-SOE v0.1B durable execution gate.

This module extends the v0.1A software-only contract gate with three bounded
properties for the harmless demo action:

* durable replay state backed by SQLite;
* transactional atomicity between the in-database demo state change and the
  durable execution record;
* an Ed25519 authority-signing boundary in which the executor receives only a
  public verification key.

The atomicity claim is intentionally narrow: it applies only to the SQLite
transaction used by the demo counter. It does not make external operating-system,
network, device, robotics, manufacturing, or other physical side effects atomic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field

from .ws_soe import (
    DEMO_ACTION,
    DEMO_TARGET,
    AuthorizationError,
    Decision,
    Intent,
    Observation,
    ReplayError,
    TargetSubstitutionError,
    UnsupportedActionError,
    WSSOEError,
    canonical_json,
    canonical_sha256,
    validate_authorization,
)

SCHEMA_VERSION = "ws-soe/v0.1b"
EXECUTION_LEDGER_SCHEMA = "WS-SOE-V0.1B-DURABLE-EXECUTION-V1"
SIGNING_ALGORITHM = "Ed25519"
SIGNING_CONTEXT = b"WS-SOE-v0.1B:Decision\x00"
_DB_NAME = "ws_soe_execution.db"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class AuthoritySignatureError(AuthorizationError):
    """The decision signature is absent, malformed, untrusted, or invalid."""


class ExecutionStoreError(WSSOEError):
    """The durable demo execution store cannot be safely used."""


class DecisionSignature(BaseModel):
    """Detached signature metadata for one canonical v0.1A Decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, pattern=r"^ws-soe/v0\.1b$")
    decision_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: str = Field(min_length=1, max_length=128)
    key_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,128}$")
    algorithm: str = Field(default=SIGNING_ALGORITHM, pattern=r"^Ed25519$")
    signature_b64url: str = Field(pattern=r"^[A-Za-z0-9_-]{80,100}$")


@runtime_checkable
class DecisionAuthoritySigner(Protocol):
    """Narrow signing interface; decision creation remains outside this object."""

    @property
    def authority(self) -> str: ...

    @property
    def key_id(self) -> str: ...

    def public_key_bytes(self) -> bytes: ...

    def sign_decision(self, decision: Decision) -> DecisionSignature: ...


def _encode_b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_b64url(value: str) -> bytes:
    if not value or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise AuthoritySignatureError("decision signature is not canonical base64url")
    padded = value + "=" * ((4 - len(value) % 4) % 4)
    try:
        decoded = base64.b64decode(
            padded.encode("ascii"),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise AuthoritySignatureError("decision signature is not valid base64url") from exc
    if _encode_b64url(decoded) != value:
        raise AuthoritySignatureError("decision signature base64url is non-canonical")
    return decoded


def _decision_signing_bytes(decision: Decision) -> bytes:
    return SIGNING_CONTEXT + canonical_json(decision).encode("utf-8")


@dataclass(frozen=True)
class LocalEd25519DecisionAuthoritySigner:
    """Software-key signer used by the v0.1B gate and tests.

    The private key is deliberately absent from the executor/verifier object.
    This is an API separation boundary, not a claim of process isolation,
    non-exportable custody, HSM protection, or hardware-backed authorization.
    """

    private_key: Ed25519PrivateKey
    authority: str
    key_id: str

    def __post_init__(self) -> None:
        if not self.authority or len(self.authority) > 128:
            raise AuthoritySignatureError("authority identifier is invalid")
        if _SAFE_ID.fullmatch(self.key_id) is None:
            raise AuthoritySignatureError("key_id is invalid")

    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign_decision(self, decision: Decision) -> DecisionSignature:
        if decision.authority != self.authority:
            raise AuthoritySignatureError(
                "signer authority does not match the decision authority"
            )
        signature = self.private_key.sign(_decision_signing_bytes(decision))
        return DecisionSignature(
            decision_hash=canonical_sha256(decision),
            authority=self.authority,
            key_id=self.key_id,
            signature_b64url=_encode_b64url(signature),
        )


@dataclass(frozen=True)
class DecisionAuthorityVerifier:
    """Public-key-only verifier supplied to the durable executor."""

    authority: str
    key_id: str
    public_key: Ed25519PublicKey

    @classmethod
    def from_raw_public_key(
        cls,
        *,
        authority: str,
        key_id: str,
        public_key_bytes: bytes,
    ) -> "DecisionAuthorityVerifier":
        if len(public_key_bytes) != 32:
            raise AuthoritySignatureError("Ed25519 public key must be exactly 32 bytes")
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except ValueError as exc:
            raise AuthoritySignatureError("Ed25519 public key is invalid") from exc
        return cls(authority=authority, key_id=key_id, public_key=public_key)

    def __post_init__(self) -> None:
        if not self.authority or len(self.authority) > 128:
            raise AuthoritySignatureError("trusted authority identifier is invalid")
        if _SAFE_ID.fullmatch(self.key_id) is None:
            raise AuthoritySignatureError("trusted key_id is invalid")

    def verify(self, decision: Decision, signature: DecisionSignature) -> None:
        if decision.authority != self.authority:
            raise AuthoritySignatureError("decision authority is not trusted")
        if signature.authority != self.authority:
            raise AuthoritySignatureError("signature authority is not trusted")
        if signature.key_id != self.key_id:
            raise AuthoritySignatureError("signature key_id is not trusted")
        expected_hash = canonical_sha256(decision)
        if signature.decision_hash != expected_hash:
            raise AuthoritySignatureError("signature is not bound to the exact decision")
        raw_signature = _decode_b64url(signature.signature_b64url)
        if len(raw_signature) != 64:
            raise AuthoritySignatureError("Ed25519 signature must be exactly 64 bytes")
        try:
            self.public_key.verify(raw_signature, _decision_signing_bytes(decision))
        except InvalidSignature as exc:
            raise AuthoritySignatureError("decision signature verification failed") from exc


@dataclass(frozen=True)
class DurableExecutionRecord:
    execution_id: str
    intent_hash: str
    intent_id: str
    decision_hash: str
    decision_json: str
    signature_hash: str
    signature_json: str
    observation_id: str
    observation_hash: str
    observation_json: str
    before_counter: int
    after_counter: int
    committed_at: str


class DurableExecutionStore:
    """SQLite store for the v0.1B harmless demo execution boundary."""

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise ExecutionStoreError("WS-SOE execution data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / _DB_NAME
        self._reject_database_symlink()
        self._initialize()

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise ExecutionStoreError(
                    "WS-SOE execution data directory must be a real directory"
                )
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise ExecutionStoreError(
                "WS-SOE execution data directory must be owned by the service UID"
            )
        if stat.S_IMODE(status.st_mode) & 0o022:
            raise ExecutionStoreError(
                "WS-SOE execution data directory must not be group/other writable"
            )

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise ExecutionStoreError(
                    "WS-SOE execution database must be a regular file"
                )
            if status.st_uid != os.geteuid():
                raise ExecutionStoreError(
                    "WS-SOE execution database must be owned by the service UID"
                )

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.db_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise ExecutionStoreError("unable to open WS-SOE execution database") from exc
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS demo_state (
                    target TEXT PRIMARY KEY,
                    counter INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT NOT NULL UNIQUE,
                    intent_hash TEXT PRIMARY KEY,
                    intent_id TEXT NOT NULL,
                    decision_hash TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    signature_hash TEXT NOT NULL,
                    signature_json TEXT NOT NULL,
                    observation_id TEXT NOT NULL UNIQUE,
                    observation_hash TEXT NOT NULL,
                    observation_json TEXT NOT NULL,
                    before_counter INTEGER NOT NULL,
                    after_counter INTEGER NOT NULL,
                    committed_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (EXECUTION_LEDGER_SCHEMA,),
            )
            schema = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if schema is None or schema["value"] != EXECUTION_LEDGER_SCHEMA:
                raise ExecutionStoreError("WS-SOE execution database schema mismatch")
            connection.execute(
                "INSERT OR IGNORE INTO demo_state(target, counter) VALUES(?, ?)",
                (DEMO_TARGET, 41),
            )
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise ExecutionStoreError("WS-SOE execution database integrity check failed")
        except sqlite3.Error as exc:
            raise ExecutionStoreError(
                "unable to initialize WS-SOE execution database"
            ) from exc
        finally:
            connection.close()
        try:
            self.db_path.chmod(0o600)
        except OSError as exc:
            raise ExecutionStoreError(
                "unable to restrict WS-SOE execution database permissions"
            ) from exc

    def counter_value(self) -> int:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT counter FROM demo_state WHERE target = ?",
                (DEMO_TARGET,),
            ).fetchone()
            if row is None:
                raise ExecutionStoreError("demo counter state is missing")
            return int(row["counter"])
        finally:
            connection.close()

    def execution_count(self) -> int:
        connection = self._connect()
        try:
            return int(connection.execute("SELECT COUNT(*) FROM executions").fetchone()[0])
        finally:
            connection.close()

    def get_execution(self, intent_hash: str) -> DurableExecutionRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM executions WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone()
            if row is None:
                return None
            return DurableExecutionRecord(
                **{name: row[name] for name in DurableExecutionRecord.__dataclass_fields__}
            )
        finally:
            connection.close()


class DurableDemoCounterExecutor:
    """Public-verifier-only executor for one transactional demo action."""

    def __init__(
        self,
        store: DurableExecutionStore,
        verifier: DecisionAuthorityVerifier,
    ) -> None:
        self.store = store
        self.verifier = verifier

    def _after_state_update(self, connection: sqlite3.Connection) -> None:
        """Test seam used to prove rollback between state mutation and commit."""

    def execute(
        self,
        intent: Intent,
        decision: Decision,
        signature: DecisionSignature,
        *,
        now: datetime,
        observation_id: str,
    ) -> Observation:
        self.verifier.verify(decision, signature)
        validate_authorization(intent, decision, now=now)
        if intent.action != DEMO_ACTION:
            raise UnsupportedActionError(f"unsupported demo action: {intent.action}")
        if intent.target != DEMO_TARGET:
            raise TargetSubstitutionError(f"unsupported demo target: {intent.target}")
        if intent.arguments != {"delta": 1}:
            raise UnsupportedActionError(
                "demo.counter.increment requires exactly {'delta': 1}"
            )

        intent_hash = canonical_sha256(intent)
        decision_hash = canonical_sha256(decision)
        signature_hash = canonical_sha256(signature)
        decision_json = canonical_json(decision)
        signature_json = canonical_json(signature)
        committed_at = now.astimezone(UTC).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        execution_id = "ws-soe-exec-" + hashlib.sha256(
            (intent_hash + decision_hash + signature_hash).encode("ascii")
        ).hexdigest()[:24]

        connection = self.store._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT execution_id FROM executions WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone()
            if existing is not None:
                raise ReplayError("intent has already been durably consumed")

            row = connection.execute(
                "SELECT counter FROM demo_state WHERE target = ?",
                (DEMO_TARGET,),
            ).fetchone()
            if row is None:
                raise ExecutionStoreError("demo counter state is missing")
            before = int(row["counter"])
            after = before + 1
            connection.execute(
                "UPDATE demo_state SET counter = ? WHERE target = ?",
                (after, DEMO_TARGET),
            )

            self._after_state_update(connection)

            observation = Observation(
                observation_id=observation_id,
                intent_hash=intent_hash,
                action=intent.action,
                target=intent.target,
                observed_at=now,
                before={"counter": before},
                after={"counter": after},
                result={"applied_delta": 1},
            )
            observation_json = canonical_json(observation)
            observation_hash = canonical_sha256(observation)
            connection.execute(
                """
                INSERT INTO executions(
                    execution_id, intent_hash, intent_id,
                    decision_hash, decision_json,
                    signature_hash, signature_json,
                    observation_id, observation_hash, observation_json,
                    before_counter, after_counter, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_id,
                    intent_hash,
                    intent.intent_id,
                    decision_hash,
                    decision_json,
                    signature_hash,
                    signature_json,
                    observation.observation_id,
                    observation_hash,
                    observation_json,
                    before,
                    after,
                    committed_at,
                ),
            )
            connection.commit()
            return observation
        except ReplayError:
            if connection.in_transaction:
                connection.rollback()
            raise
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise ExecutionStoreError(
                "durable execution record conflicts with an existing record"
            ) from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

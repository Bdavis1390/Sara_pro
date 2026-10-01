"""WS-SOE v0.1C external-effect reconciliation gate.

v0.1C deliberately moves one step beyond the v0.1B same-database transaction
without pretending that an external effect can participate in that local
transaction.  It demonstrates a bounded recovery pattern against a harmless
mock external counter service that owns a separate SQLite database.

The core rule is simple: an ambiguous dispatch outcome is not classified as
failure.  The coordinator persists UNCERTAIN (or recovers a stale DISPATCHING
record), queries the external service by a deterministic idempotency key, and
reconciles before any retry is permitted.

This is a software-only demonstration.  It does not establish distributed
exactly-once semantics, a production RPC protocol, Byzantine tolerance, hardware
attestation, live service authorization, or safety for physical side effects.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .ws_soe import (
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
from .ws_soe_v01b import (
    DecisionAuthorityVerifier,
    DecisionSignature,
)

SCHEMA_VERSION = "ws-soe/v0.1c"
EXTERNAL_ACTION = "demo.external.counter.increment"
EXTERNAL_TARGET = "demo.external.counter"
LOCAL_LEDGER_SCHEMA = "WS-SOE-V0.1C-LOCAL-COORDINATOR-V1"
EXTERNAL_LEDGER_SCHEMA = "WS-SOE-V0.1C-MOCK-EXTERNAL-V1"
_LOCAL_DB_NAME = "ws_soe_v01c_coordinator.db"
_EXTERNAL_DB_NAME = "ws_soe_v01c_external.db"


class ExternalEffectError(WSSOEError):
    """Base failure for the bounded v0.1C external-effect demonstration."""


class ExternalAcknowledgementLost(ExternalEffectError):
    """The external effect committed, but its acknowledgement was not delivered."""


class ExternalEffectUncertain(ExternalEffectError):
    """The caller cannot determine whether the external effect occurred."""


class ExternalRequestConflict(ExternalEffectError):
    """An idempotency key was reused for non-identical external request bytes."""


class ReconciliationError(ExternalEffectError):
    """Durable local and external evidence cannot be safely reconciled."""


class CoordinatorStateError(ExternalEffectError):
    """The local coordinator state does not permit the requested transition."""


class ExecutionStoreError(ExternalEffectError):
    """A v0.1C SQLite store cannot be safely used."""


class InjectedCoordinatorCrash(RuntimeError):
    """Harmless fault-injection seam used only by the v0.1C tests."""


class ExternalOperationState(str, Enum):
    PREPARED = "PREPARED"
    DISPATCHING = "DISPATCHING"
    UNCERTAIN = "UNCERTAIN"
    EFFECT_OBSERVED = "EFFECT_OBSERVED"
    NO_EFFECT_CONFIRMED = "NO_EFFECT_CONFIRMED"
    RECONCILED = "RECONCILED"
    SEALED = "SEALED"


class ExternalRequest(BaseModel):
    """Canonical request understood by the harmless mock external service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, pattern=r"^ws-soe/v0\.1c$")
    idempotency_key: str = Field(pattern=r"^ws-soe-v01c-[0-9a-f]{32}$")
    intent_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    arguments: dict[str, int]


class ExternalEffect(BaseModel):
    """Durable result returned by the mock external service."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default=SCHEMA_VERSION, pattern=r"^ws-soe/v0\.1c$")
    idempotency_key: str = Field(pattern=r"^ws-soe-v01c-[0-9a-f]{32}$")
    request_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    before_counter: int
    after_counter: int
    committed_at: AwareDatetime


class ReconciliationResult(BaseModel):
    """Outcome of one explicit reconciliation attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    effect_found: bool
    state: ExternalOperationState
    observation: Observation | None = None


@dataclass(frozen=True)
class CoordinatorRecord:
    intent_hash: str
    intent_id: str
    decision_hash: str
    decision_json: str
    signature_hash: str
    signature_json: str
    request_hash: str
    request_json: str
    idempotency_key: str
    state: str
    observation_hash: str | None
    observation_json: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TransitionRecord:
    sequence: int
    intent_hash: str
    from_state: str | None
    to_state: str
    reason: str
    transitioned_at: str


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _prepare_secure_dir(path: Path) -> None:
    if not path.is_absolute():
        raise ExecutionStoreError("WS-SOE v0.1C data directory must be absolute")
    if path.exists():
        status = path.lstat()
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise ExecutionStoreError("WS-SOE v0.1C data directory must be a real directory")
    else:
        path.mkdir(parents=True, mode=0o700)
        status = path.lstat()
    if status.st_uid != os.geteuid():
        raise ExecutionStoreError("WS-SOE v0.1C data directory must be owned by the service UID")
    if stat.S_IMODE(status.st_mode) & 0o022:
        raise ExecutionStoreError(
            "WS-SOE v0.1C data directory must not be group/other writable"
        )


def _reject_unsafe_db(path: Path) -> None:
    if not (path.exists() or path.is_symlink()):
        return
    status = path.lstat()
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
        raise ExecutionStoreError("WS-SOE v0.1C database must be a regular file")
    if status.st_uid != os.geteuid():
        raise ExecutionStoreError("WS-SOE v0.1C database must be owned by the service UID")


def _connect(path: Path) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    except sqlite3.Error as exc:
        raise ExecutionStoreError("unable to open WS-SOE v0.1C database") from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _secure_mode(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError as exc:
        raise ExecutionStoreError("unable to restrict WS-SOE v0.1C database permissions") from exc


def _request_for_intent(intent: Intent) -> ExternalRequest:
    intent_hash = canonical_sha256(intent)
    suffix = hashlib.sha256(intent_hash.encode("ascii")).hexdigest()[:32]
    return ExternalRequest(
        idempotency_key=f"ws-soe-v01c-{suffix}",
        intent_hash=intent_hash,
        action=intent.action,
        target=intent.target,
        arguments=intent.arguments,
    )


class MockExternalCounterService:
    """Separate durable mock service used to model an external side effect.

    The service owns a different SQLite database from the coordinator and
    enforces one request body per idempotency key.  Repeated identical requests
    return the first committed effect without incrementing again.
    """

    def __init__(self, data_dir: str | Path) -> None:
        self.data_dir = Path(data_dir)
        _prepare_secure_dir(self.data_dir)
        self.db_path = self.data_dir / _EXTERNAL_DB_NAME
        _reject_unsafe_db(self.db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return _connect(self.db_path)

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
                CREATE TABLE IF NOT EXISTS external_state (
                    target TEXT PRIMARY KEY,
                    counter INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS effects (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    before_counter INTEGER NOT NULL,
                    after_counter INTEGER NOT NULL,
                    committed_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (EXTERNAL_LEDGER_SCHEMA,),
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if row is None or row["value"] != EXTERNAL_LEDGER_SCHEMA:
                raise ExecutionStoreError("mock external database schema mismatch")
            connection.execute(
                "INSERT OR IGNORE INTO external_state(target, counter) VALUES(?, 41)",
                (EXTERNAL_TARGET,),
            )
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise ExecutionStoreError("mock external database integrity check failed")
        except sqlite3.Error as exc:
            raise ExecutionStoreError("unable to initialize mock external database") from exc
        finally:
            connection.close()
        _secure_mode(self.db_path)

    def counter_value(self) -> int:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT counter FROM external_state WHERE target = ?",
                (EXTERNAL_TARGET,),
            ).fetchone()
            if row is None:
                raise ExecutionStoreError("mock external counter state is missing")
            return int(row["counter"])
        finally:
            connection.close()

    def effect_count(self) -> int:
        connection = self._connect()
        try:
            return int(connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0])
        finally:
            connection.close()

    def lookup(self, idempotency_key: str) -> ExternalEffect | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM effects WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is None:
                return None
            return ExternalEffect(
                idempotency_key=row["idempotency_key"],
                request_hash=row["request_hash"],
                before_counter=int(row["before_counter"]),
                after_counter=int(row["after_counter"]),
                committed_at=datetime.fromisoformat(row["committed_at"].replace("Z", "+00:00")),
            )
        finally:
            connection.close()

    def apply(
        self,
        request: ExternalRequest,
        *,
        now: datetime,
        fault: str | None = None,
    ) -> ExternalEffect:
        if request.action != EXTERNAL_ACTION:
            raise UnsupportedActionError(f"unsupported external demo action: {request.action}")
        if request.target != EXTERNAL_TARGET:
            raise TargetSubstitutionError(f"unsupported external demo target: {request.target}")
        if request.arguments != {"delta": 1}:
            raise UnsupportedActionError(
                "demo.external.counter.increment requires exactly {'delta': 1}"
            )
        if fault not in {None, "after_commit_before_ack"}:
            raise ValueError(f"unsupported external fault injection: {fault}")

        request_hash = canonical_sha256(request)
        committed_at = _utc_text(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM effects WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise ExternalRequestConflict(
                        "idempotency key is already bound to different request bytes"
                    )
                effect = ExternalEffect(
                    idempotency_key=existing["idempotency_key"],
                    request_hash=existing["request_hash"],
                    before_counter=int(existing["before_counter"]),
                    after_counter=int(existing["after_counter"]),
                    committed_at=datetime.fromisoformat(
                        existing["committed_at"].replace("Z", "+00:00")
                    ),
                )
                connection.commit()
                return effect

            row = connection.execute(
                "SELECT counter FROM external_state WHERE target = ?",
                (EXTERNAL_TARGET,),
            ).fetchone()
            if row is None:
                raise ExecutionStoreError("mock external counter state is missing")
            before = int(row["counter"])
            after = before + 1
            connection.execute(
                "UPDATE external_state SET counter = ? WHERE target = ?",
                (after, EXTERNAL_TARGET),
            )
            connection.execute(
                """
                INSERT INTO effects(
                    idempotency_key, request_hash, request_json,
                    before_counter, after_counter, committed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    request.idempotency_key,
                    request_hash,
                    canonical_json(request),
                    before,
                    after,
                    committed_at,
                ),
            )
            connection.commit()
            effect = ExternalEffect(
                idempotency_key=request.idempotency_key,
                request_hash=request_hash,
                before_counter=before,
                after_counter=after,
                committed_at=now,
            )
        except ExternalRequestConflict:
            if connection.in_transaction:
                connection.rollback()
            raise
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

        if fault == "after_commit_before_ack":
            raise ExternalAcknowledgementLost(
                "mock external effect committed but acknowledgement was lost"
            )
        return effect


class ExternalReconciliationCoordinator:
    """Durable coordinator that never blindly retries an ambiguous dispatch."""

    def __init__(
        self,
        data_dir: str | Path,
        verifier: DecisionAuthorityVerifier,
        external_service: MockExternalCounterService,
    ) -> None:
        self.data_dir = Path(data_dir)
        _prepare_secure_dir(self.data_dir)
        self.db_path = self.data_dir / _LOCAL_DB_NAME
        _reject_unsafe_db(self.db_path)
        self.verifier = verifier
        self.external_service = external_service
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return _connect(self.db_path)

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
                CREATE TABLE IF NOT EXISTS operations (
                    intent_hash TEXT PRIMARY KEY,
                    intent_id TEXT NOT NULL,
                    decision_hash TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    signature_hash TEXT NOT NULL,
                    signature_json TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    observation_hash TEXT,
                    observation_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_hash TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    transitioned_at TEXT NOT NULL,
                    FOREIGN KEY(intent_hash) REFERENCES operations(intent_hash)
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (LOCAL_LEDGER_SCHEMA,),
            )
            row = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if row is None or row["value"] != LOCAL_LEDGER_SCHEMA:
                raise ExecutionStoreError("v0.1C coordinator database schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise ExecutionStoreError("v0.1C coordinator database integrity check failed")
        except sqlite3.Error as exc:
            raise ExecutionStoreError("unable to initialize v0.1C coordinator database") from exc
        finally:
            connection.close()
        _secure_mode(self.db_path)

    def _validate_inputs(
        self,
        intent: Intent,
        decision,
        signature: DecisionSignature,
        *,
        now: datetime,
    ) -> ExternalRequest:
        self.verifier.verify(decision, signature)
        validate_authorization(intent, decision, now=now)
        if intent.action != EXTERNAL_ACTION:
            raise UnsupportedActionError(f"unsupported external demo action: {intent.action}")
        if intent.target != EXTERNAL_TARGET:
            raise TargetSubstitutionError(f"unsupported external demo target: {intent.target}")
        if intent.arguments != {"delta": 1}:
            raise UnsupportedActionError(
                "demo.external.counter.increment requires exactly {'delta': 1}"
            )
        return _request_for_intent(intent)

    def get_record(self, intent_hash: str) -> CoordinatorRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM operations WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone()
            if row is None:
                return None
            return CoordinatorRecord(
                **{name: row[name] for name in CoordinatorRecord.__dataclass_fields__}
            )
        finally:
            connection.close()

    def transition_history(self, intent_hash: str) -> list[TransitionRecord]:
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM transitions WHERE intent_hash = ? ORDER BY sequence",
                (intent_hash,),
            ).fetchall()
            return [
                TransitionRecord(
                    **{name: row[name] for name in TransitionRecord.__dataclass_fields__}
                )
                for row in rows
            ]
        finally:
            connection.close()

    def _insert_prepared(
        self,
        intent: Intent,
        decision,
        signature: DecisionSignature,
        request: ExternalRequest,
        *,
        now: datetime,
    ) -> None:
        intent_hash = canonical_sha256(intent)
        decision_hash = canonical_sha256(decision)
        signature_hash = canonical_sha256(signature)
        request_hash = canonical_sha256(request)
        timestamp = _utc_text(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM operations WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone() is not None:
                raise ReplayError(
                    "intent already has a durable external-operation record; reconcile explicitly"
                )
            connection.execute(
                """
                INSERT INTO operations(
                    intent_hash, intent_id,
                    decision_hash, decision_json,
                    signature_hash, signature_json,
                    request_hash, request_json, idempotency_key,
                    state, observation_hash, observation_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                """,
                (
                    intent_hash,
                    intent.intent_id,
                    decision_hash,
                    canonical_json(decision),
                    signature_hash,
                    canonical_json(signature),
                    request_hash,
                    canonical_json(request),
                    request.idempotency_key,
                    ExternalOperationState.PREPARED.value,
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO transitions(intent_hash, from_state, to_state, reason, transitioned_at)
                VALUES (?, NULL, ?, ?, ?)
                """,
                (
                    intent_hash,
                    ExternalOperationState.PREPARED.value,
                    "authorization verified and external request durably prepared",
                    timestamp,
                ),
            )
            connection.commit()
        except ReplayError:
            if connection.in_transaction:
                connection.rollback()
            raise
        except sqlite3.IntegrityError as exc:
            if connection.in_transaction:
                connection.rollback()
            raise ReplayError("external-operation identity is already present") from exc
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _transition(
        self,
        intent_hash: str,
        *,
        expected: set[ExternalOperationState],
        to_state: ExternalOperationState,
        reason: str,
        now: datetime,
    ) -> None:
        timestamp = _utc_text(now)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM operations WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone()
            if row is None:
                raise CoordinatorStateError("external operation record is missing")
            current = ExternalOperationState(row["state"])
            if current not in expected:
                raise CoordinatorStateError(
                    f"cannot transition external operation from {current.value} to {to_state.value}"
                )
            connection.execute(
                "UPDATE operations SET state = ?, updated_at = ? WHERE intent_hash = ?",
                (to_state.value, timestamp, intent_hash),
            )
            connection.execute(
                """
                INSERT INTO transitions(intent_hash, from_state, to_state, reason, transitioned_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (intent_hash, current.value, to_state.value, reason, timestamp),
            )
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _seal_effect(
        self,
        intent_hash: str,
        effect: ExternalEffect,
        *,
        now: datetime,
        observation_id: str,
        allowed_from: set[ExternalOperationState],
    ) -> Observation:
        record = self.get_record(intent_hash)
        if record is None:
            raise CoordinatorStateError("external operation record is missing")
        if effect.idempotency_key != record.idempotency_key:
            raise ReconciliationError("external effect idempotency key does not match local record")
        if effect.request_hash != record.request_hash:
            raise ReconciliationError("external effect request hash does not match local record")

        request = ExternalRequest.model_validate(json.loads(record.request_json))
        observation = Observation(
            observation_id=observation_id,
            intent_hash=intent_hash,
            action=request.action,
            target=request.target,
            observed_at=effect.committed_at,
            before={"counter": effect.before_counter},
            after={"counter": effect.after_counter},
            result={
                "applied_delta": 1,
                "external_idempotency_key": effect.idempotency_key,
                "external_request_hash": effect.request_hash,
                "reconciled": True,
            },
        )
        observation_hash = canonical_sha256(observation)
        timestamp = _utc_text(now)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM operations WHERE intent_hash = ?",
                (intent_hash,),
            ).fetchone()
            if row is None:
                raise CoordinatorStateError("external operation record is missing")
            current = ExternalOperationState(row["state"])
            if current not in allowed_from:
                raise CoordinatorStateError(
                    f"cannot seal observed effect from coordinator state {current.value}"
                )

            state = current
            for next_state, reason in (
                (
                    ExternalOperationState.EFFECT_OBSERVED,
                    "external durable effect found and request binding verified",
                ),
                (
                    ExternalOperationState.RECONCILED,
                    "external effect reconciled against durable local request",
                ),
                (
                    ExternalOperationState.SEALED,
                    "reconciled observation durably sealed",
                ),
            ):
                connection.execute(
                    "UPDATE operations SET state = ?, updated_at = ? WHERE intent_hash = ?",
                    (next_state.value, timestamp, intent_hash),
                )
                connection.execute(
                    """
                    INSERT INTO transitions(intent_hash, from_state, to_state, reason, transitioned_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (intent_hash, state.value, next_state.value, reason, timestamp),
                )
                state = next_state

            connection.execute(
                """
                UPDATE operations
                SET observation_hash = ?, observation_json = ?, updated_at = ?
                WHERE intent_hash = ?
                """,
                (
                    observation_hash,
                    canonical_json(observation),
                    timestamp,
                    intent_hash,
                ),
            )
            connection.commit()
            return observation
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def execute(
        self,
        intent: Intent,
        decision,
        signature: DecisionSignature,
        *,
        now: datetime,
        observation_id: str,
        fault: str | None = None,
    ) -> Observation:
        if fault not in {
            None,
            "crash_before_external_call",
            "after_external_commit_before_ack",
            "after_external_ack_before_local_record",
        }:
            raise ValueError(f"unsupported coordinator fault injection: {fault}")

        request = self._validate_inputs(intent, decision, signature, now=now)
        intent_hash = canonical_sha256(intent)
        self._insert_prepared(intent, decision, signature, request, now=now)
        self._transition(
            intent_hash,
            expected={ExternalOperationState.PREPARED},
            to_state=ExternalOperationState.DISPATCHING,
            reason="dispatch started with durable idempotency key",
            now=now,
        )

        if fault == "crash_before_external_call":
            raise InjectedCoordinatorCrash("injected crash before external service call")

        try:
            effect = self.external_service.apply(
                request,
                now=now,
                fault=(
                    "after_commit_before_ack"
                    if fault == "after_external_commit_before_ack"
                    else None
                ),
            )
        except ExternalAcknowledgementLost as exc:
            self._transition(
                intent_hash,
                expected={ExternalOperationState.DISPATCHING},
                to_state=ExternalOperationState.UNCERTAIN,
                reason="external acknowledgement lost; effect outcome requires reconciliation",
                now=now,
            )
            raise ExternalEffectUncertain(
                "external effect outcome is uncertain; reconciliation is required before retry"
            ) from exc

        if fault == "after_external_ack_before_local_record":
            raise InjectedCoordinatorCrash(
                "injected crash after external acknowledgement but before local observation"
            )

        return self._seal_effect(
            intent_hash,
            effect,
            now=now,
            observation_id=observation_id,
            allowed_from={ExternalOperationState.DISPATCHING},
        )

    def reconcile(
        self,
        intent_hash: str,
        *,
        now: datetime,
        observation_id: str,
    ) -> ReconciliationResult:
        record = self.get_record(intent_hash)
        if record is None:
            raise CoordinatorStateError("external operation record is missing")
        state = ExternalOperationState(record.state)
        if state not in {ExternalOperationState.DISPATCHING, ExternalOperationState.UNCERTAIN}:
            raise CoordinatorStateError(
                f"reconciliation requires DISPATCHING or UNCERTAIN, found {state.value}"
            )

        effect = self.external_service.lookup(record.idempotency_key)
        if effect is None:
            self._transition(
                intent_hash,
                expected={state},
                to_state=ExternalOperationState.NO_EFFECT_CONFIRMED,
                reason="external lookup found no durable effect for idempotency key",
                now=now,
            )
            return ReconciliationResult(
                effect_found=False,
                state=ExternalOperationState.NO_EFFECT_CONFIRMED,
            )

        observation = self._seal_effect(
            intent_hash,
            effect,
            now=now,
            observation_id=observation_id,
            allowed_from={state},
        )
        return ReconciliationResult(
            effect_found=True,
            state=ExternalOperationState.SEALED,
            observation=observation,
        )

    def redispatch_after_no_effect(
        self,
        intent_hash: str,
        *,
        now: datetime,
        observation_id: str,
        fault: str | None = None,
    ) -> Observation:
        if fault not in {None, "after_commit_before_ack"}:
            raise ValueError(f"unsupported redispatch fault injection: {fault}")
        record = self.get_record(intent_hash)
        if record is None:
            raise CoordinatorStateError("external operation record is missing")
        if ExternalOperationState(record.state) != ExternalOperationState.NO_EFFECT_CONFIRMED:
            raise CoordinatorStateError(
                "redispatch is permitted only after explicit NO_EFFECT_CONFIRMED reconciliation"
            )

        request = ExternalRequest.model_validate(json.loads(record.request_json))
        if canonical_sha256(request) != record.request_hash:
            raise ReconciliationError("durable external request bytes do not match stored hash")

        self._transition(
            intent_hash,
            expected={ExternalOperationState.NO_EFFECT_CONFIRMED},
            to_state=ExternalOperationState.DISPATCHING,
            reason="explicit redispatch after confirmed absence of external effect",
            now=now,
        )
        try:
            effect = self.external_service.apply(request, now=now, fault=fault)
        except ExternalAcknowledgementLost as exc:
            self._transition(
                intent_hash,
                expected={ExternalOperationState.DISPATCHING},
                to_state=ExternalOperationState.UNCERTAIN,
                reason="redispatch acknowledgement lost; reconcile before any further retry",
                now=now,
            )
            raise ExternalEffectUncertain(
                "redispatch outcome is uncertain; reconciliation is required"
            ) from exc

        return self._seal_effect(
            intent_hash,
            effect,
            now=now,
            observation_id=observation_id,
            allowed_from={ExternalOperationState.DISPATCHING},
        )

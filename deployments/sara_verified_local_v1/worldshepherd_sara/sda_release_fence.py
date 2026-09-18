from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from .prime_sentinel_authorization import PrimeSentinelAuthorizationError
from .qualification import canonical_digest
from .sda_release_authorization import (
    SdaReleaseCandidate,
    SdaReleaseReceipt,
    VerifiedSdaReleaseAuthorization,
    assert_release_candidate_matches_authorization,
)


SDA_RELEASE_FENCE_SCHEMA = "WS-SDA-RELEASE-FENCE-V1"
DEFAULT_CLAIM_LEASE = timedelta(seconds=30)
MAX_FENCE_RECORDS = 4096


class SdaReleaseFenceError(RuntimeError):
    pass


class SdaReleaseFenceConflict(SdaReleaseFenceError):
    pass


class SdaReleaseFenceFull(SdaReleaseFenceError):
    pass


class SdaReleaseFenceState(str, Enum):
    VERIFIED = "VERIFIED"
    CLAIMED = "CLAIMED"
    INVOKING = "INVOKING"
    CONSUMED = "CONSUMED"
    INDETERMINATE = "INDETERMINATE"


class SdaReleaseFenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authorization_id: str
    state: SdaReleaseFenceState
    candidate_digest: str
    claim_owner: str | None = None
    claimed_at: datetime | None = None
    claim_expires_at: datetime | None = None
    invoking_at: datetime | None = None
    finalized_at: datetime | None = None
    attempt_count: int
    result_evidence_ref: str | None = None
    receipt: SdaReleaseReceipt | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_time(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SdaReleaseFenceError("stored release-fence timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def _token_hash(token: str) -> str:
    if not isinstance(token, str) or len(token) < 16:
        raise SdaReleaseFenceError("claim token must contain at least 16 characters")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _candidate_digest(candidate: SdaReleaseCandidate) -> str:
    return canonical_digest(candidate)


def _authorization_document(auth: VerifiedSdaReleaseAuthorization) -> str:
    return json.dumps(
        auth.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _candidate_document(candidate: SdaReleaseCandidate) -> str:
    return json.dumps(
        candidate.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


class SdaReleaseExecutionFence:
    """Durable cross-process fence for one human-authorized analytic release.

    State machine:

        VERIFIED -> CLAIMED -> INVOKING -> CONSUMED
                                   |
                                   +------> INDETERMINATE

    Only CLAIMED leases may expire and be reclaimed. Once INVOKING is durable,
    automatic retry is forbidden because the external side effect may have happened
    even if acknowledgement was lost.

    The fence serializes state transitions with SQLite BEGIN IMMEDIATE. It is a
    reference-software cross-process transaction boundary on one shared database;
    it is not distributed consensus or proof of external delivery.
    """

    def __init__(
        self,
        data_dir: str | Path,
        *,
        claim_lease: timedelta = DEFAULT_CLAIM_LEASE,
    ) -> None:
        if claim_lease <= timedelta(0) or claim_lease > timedelta(minutes=5):
            raise SdaReleaseFenceError("claim lease must be >0 and <=5 minutes")
        self.claim_lease = claim_lease
        self.data_dir = Path(data_dir)
        if not self.data_dir.is_absolute():
            raise SdaReleaseFenceError("release-fence data directory must be absolute")
        self._prepare_data_dir()
        self.db_path = self.data_dir / "sda-release-fence.db"
        self._reject_database_symlink()
        self._initialize()

    def _prepare_data_dir(self) -> None:
        if self.data_dir.exists():
            status = self.data_dir.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise SdaReleaseFenceError("release-fence data directory must be a real directory")
        else:
            self.data_dir.mkdir(parents=True, mode=0o700)
            status = self.data_dir.lstat()
        if status.st_uid != os.geteuid():
            raise SdaReleaseFenceError("release-fence data directory must be owned by service UID")
        if stat.S_IMODE(status.st_mode) != 0o700:
            self.data_dir.chmod(0o700)
            if stat.S_IMODE(self.data_dir.stat().st_mode) != 0o700:
                raise SdaReleaseFenceError("release-fence data directory must be mode 0700")

    def _reject_database_symlink(self) -> None:
        if self.db_path.exists() or self.db_path.is_symlink():
            status = self.db_path.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
                raise SdaReleaseFenceError("release-fence database must be a regular file")
            if status.st_uid != os.geteuid():
                raise SdaReleaseFenceError("release-fence database must be owned by service UID")

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self.db_path,
                timeout=5.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise SdaReleaseFenceError("unable to open release-fence database") from exc
        connection.row_factory = sqlite3.Row
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
                CREATE TABLE IF NOT EXISTS releases (
                    authorization_id TEXT PRIMARY KEY,
                    authorization_json TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    candidate_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    claim_owner TEXT,
                    claim_token_sha256 TEXT,
                    claimed_at TEXT,
                    claim_expires_at TEXT,
                    invoking_at TEXT,
                    finalized_at TEXT,
                    attempt_count INTEGER NOT NULL CHECK(attempt_count >= 0),
                    result_evidence_ref TEXT,
                    receipt_json TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    authorization_id TEXT NOT NULL,
                    from_state TEXT,
                    to_state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    evidence_ref TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_release_fence_state
                    ON releases(state);
                CREATE INDEX IF NOT EXISTS idx_release_fence_transition_auth
                    ON transitions(authorization_id, sequence);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(name, value) VALUES('schema', ?)",
                (SDA_RELEASE_FENCE_SCHEMA,),
            )
            schema = connection.execute(
                "SELECT value FROM metadata WHERE name='schema'"
            ).fetchone()
            if schema is None or schema["value"] != SDA_RELEASE_FENCE_SCHEMA:
                raise SdaReleaseFenceError("release-fence schema mismatch")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise SdaReleaseFenceError("release-fence database integrity check failed")
        except sqlite3.Error as exc:
            raise SdaReleaseFenceError("unable to initialize release-fence database") from exc
        finally:
            connection.close()
        self.db_path.chmod(0o600)

    def register_verified(
        self,
        authorization: VerifiedSdaReleaseAuthorization,
        candidate: SdaReleaseCandidate,
        *,
        now: datetime | None = None,
        actor: str = "SARA",
    ) -> SdaReleaseFenceRecord:
        current = (now or _utc_now()).astimezone(timezone.utc)
        assert_release_candidate_matches_authorization(
            authorization,
            candidate,
            now=current,
        )
        digest = _candidate_digest(candidate)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM releases WHERE authorization_id=?",
                (authorization.authorization_id,),
            ).fetchone()
            if row is not None:
                if row["candidate_digest"] != digest:
                    raise SdaReleaseFenceConflict(
                        "authorization ID is already bound to different release semantics"
                    )
                connection.commit()
                return self._row_to_record(row)

            count = connection.execute("SELECT COUNT(*) FROM releases").fetchone()[0]
            if count >= MAX_FENCE_RECORDS:
                raise SdaReleaseFenceFull("release-fence capacity reached")

            connection.execute(
                """
                INSERT INTO releases(
                    authorization_id, authorization_json, candidate_json,
                    candidate_digest, state, attempt_count
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    authorization.authorization_id,
                    _authorization_document(authorization),
                    _candidate_document(candidate),
                    digest,
                    SdaReleaseFenceState.VERIFIED.value,
                ),
            )
            self._transition(
                connection,
                authorization.authorization_id,
                None,
                SdaReleaseFenceState.VERIFIED,
                current,
                actor,
                None,
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM releases WHERE authorization_id=?",
                (authorization.authorization_id,),
            ).fetchone()
            assert row is not None
            return self._row_to_record(row)
        except (sqlite3.Error, SdaReleaseFenceError, PrimeSentinelAuthorizationError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def claim(
        self,
        authorization_id: str,
        candidate: SdaReleaseCandidate,
        *,
        owner: str,
        claim_token: str,
        now: datetime | None = None,
    ) -> SdaReleaseFenceRecord:
        current = (now or _utc_now()).astimezone(timezone.utc)
        if not owner or len(owner) > 128:
            raise SdaReleaseFenceError("claim owner must contain 1-128 characters")
        token_digest = _token_hash(claim_token)
        candidate_digest = _candidate_digest(candidate)

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._required_row(connection, authorization_id)
            self._assert_candidate(row, candidate_digest)
            state = SdaReleaseFenceState(row["state"])

            if state in {
                SdaReleaseFenceState.INVOKING,
                SdaReleaseFenceState.CONSUMED,
                SdaReleaseFenceState.INDETERMINATE,
            }:
                raise SdaReleaseFenceConflict(
                    f"release cannot be claimed from terminal/unsafe state {state.value}"
                )

            if state == SdaReleaseFenceState.CLAIMED:
                expiry = _parse_time(row["claim_expires_at"])
                if expiry is None or current < expiry:
                    raise SdaReleaseFenceConflict("release already has an active claim")
                # Reclaim is permitted only because INVOKING was never durably entered.

            authorization = VerifiedSdaReleaseAuthorization.model_validate_json(
                row["authorization_json"]
            )
            assert_release_candidate_matches_authorization(
                authorization,
                candidate,
                now=current,
            )

            from_state = state
            expires = current + self.claim_lease
            connection.execute(
                """
                UPDATE releases
                SET state=?, claim_owner=?, claim_token_sha256=?,
                    claimed_at=?, claim_expires_at=?, attempt_count=attempt_count+1
                WHERE authorization_id=?
                """,
                (
                    SdaReleaseFenceState.CLAIMED.value,
                    owner,
                    token_digest,
                    _utc_text(current),
                    _utc_text(expires),
                    authorization_id,
                ),
            )
            self._transition(
                connection,
                authorization_id,
                from_state,
                SdaReleaseFenceState.CLAIMED,
                current,
                owner,
                None,
            )
            connection.commit()
            return self._fetch_record(connection, authorization_id)
        except (sqlite3.Error, SdaReleaseFenceError, PrimeSentinelAuthorizationError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def mark_invoking(
        self,
        authorization_id: str,
        candidate: SdaReleaseCandidate,
        *,
        owner: str,
        claim_token: str,
        now: datetime | None = None,
    ) -> SdaReleaseFenceRecord:
        current = (now or _utc_now()).astimezone(timezone.utc)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._required_row(connection, authorization_id)
            self._assert_claim(row, owner, claim_token, current)
            self._assert_candidate(row, _candidate_digest(candidate))
            authorization = VerifiedSdaReleaseAuthorization.model_validate_json(
                row["authorization_json"]
            )
            assert_release_candidate_matches_authorization(
                authorization,
                candidate,
                now=current,
            )
            connection.execute(
                """
                UPDATE releases
                SET state=?, invoking_at=?, claim_expires_at=NULL
                WHERE authorization_id=?
                """,
                (
                    SdaReleaseFenceState.INVOKING.value,
                    _utc_text(current),
                    authorization_id,
                ),
            )
            self._transition(
                connection,
                authorization_id,
                SdaReleaseFenceState.CLAIMED,
                SdaReleaseFenceState.INVOKING,
                current,
                owner,
                None,
            )
            connection.commit()
            return self._fetch_record(connection, authorization_id)
        except (sqlite3.Error, SdaReleaseFenceError, PrimeSentinelAuthorizationError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def finalize_success(
        self,
        authorization_id: str,
        *,
        owner: str,
        claim_token: str,
        result_evidence_ref: str,
        now: datetime | None = None,
    ) -> SdaReleaseFenceRecord:
        return self._finalize(
            authorization_id,
            owner=owner,
            claim_token=claim_token,
            result_evidence_ref=result_evidence_ref,
            target=SdaReleaseFenceState.CONSUMED,
            now=now,
        )

    def finalize_indeterminate(
        self,
        authorization_id: str,
        *,
        owner: str,
        claim_token: str,
        result_evidence_ref: str,
        now: datetime | None = None,
    ) -> SdaReleaseFenceRecord:
        return self._finalize(
            authorization_id,
            owner=owner,
            claim_token=claim_token,
            result_evidence_ref=result_evidence_ref,
            target=SdaReleaseFenceState.INDETERMINATE,
            now=now,
        )

    def _finalize(
        self,
        authorization_id: str,
        *,
        owner: str,
        claim_token: str,
        result_evidence_ref: str,
        target: SdaReleaseFenceState,
        now: datetime | None,
    ) -> SdaReleaseFenceRecord:
        current = (now or _utc_now()).astimezone(timezone.utc)
        if not result_evidence_ref or len(result_evidence_ref) > 512:
            raise SdaReleaseFenceError("result_evidence_ref must contain 1-512 characters")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._required_row(connection, authorization_id)
            if SdaReleaseFenceState(row["state"]) != SdaReleaseFenceState.INVOKING:
                raise SdaReleaseFenceConflict(
                    "release may be finalized only from INVOKING"
                )
            self._assert_claim_token_and_owner(row, owner, claim_token)

            receipt_json: str | None = None
            if target == SdaReleaseFenceState.CONSUMED:
                authorization = VerifiedSdaReleaseAuthorization.model_validate_json(
                    row["authorization_json"]
                )
                candidate = SdaReleaseCandidate.model_validate_json(row["candidate_json"])
                receipt = SdaReleaseReceipt(
                    authorization_id=authorization.authorization_id,
                    payload_digest=candidate.payload_digest,
                    hypothesis_set_digest=candidate.hypothesis_set_digest,
                    policy_revision_digest=candidate.policy_revision_digest,
                    destination=candidate.destination,
                    releasability_tags=list(candidate.releasability_tags),
                    human_approval_id=authorization.human_approval_id,
                    human_approver=authorization.human_approver,
                    signing_key_id=authorization.key_id,
                    signing_key_fingerprint_sha256=authorization.key_fingerprint_sha256,
                    consumed_at=current,
                )
                receipt_json = json.dumps(
                    receipt.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                )

            connection.execute(
                """
                UPDATE releases
                SET state=?, finalized_at=?, result_evidence_ref=?, receipt_json=?
                WHERE authorization_id=?
                """,
                (
                    target.value,
                    _utc_text(current),
                    result_evidence_ref,
                    receipt_json,
                    authorization_id,
                ),
            )
            self._transition(
                connection,
                authorization_id,
                SdaReleaseFenceState.INVOKING,
                target,
                current,
                owner,
                result_evidence_ref,
            )
            connection.commit()
            return self._fetch_record(connection, authorization_id)
        except (sqlite3.Error, SdaReleaseFenceError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, authorization_id: str) -> SdaReleaseFenceRecord | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM releases WHERE authorization_id=?",
                (authorization_id,),
            ).fetchone()
            return None if row is None else self._row_to_record(row)
        finally:
            connection.close()

    def transitions(self, authorization_id: str) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT sequence, from_state, to_state, occurred_at, actor, evidence_ref
                FROM transitions
                WHERE authorization_id=?
                ORDER BY sequence
                """,
                (authorization_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    def health(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            quick = connection.execute("PRAGMA quick_check").fetchone()
            quick_ok = quick is not None and quick[0] == "ok"
            rows = connection.execute("SELECT * FROM releases").fetchall()
        except sqlite3.Error as exc:
            raise SdaReleaseFenceError("unable to inspect release-fence database") from exc
        finally:
            connection.close()

        malformed = 0
        for row in rows:
            try:
                authorization = VerifiedSdaReleaseAuthorization.model_validate_json(
                    row["authorization_json"]
                )
                candidate = SdaReleaseCandidate.model_validate_json(row["candidate_json"])
                if authorization.authorization_id != row["authorization_id"]:
                    malformed += 1
                elif _candidate_digest(candidate) != row["candidate_digest"]:
                    malformed += 1
                elif row["receipt_json"]:
                    receipt = SdaReleaseReceipt.model_validate_json(row["receipt_json"])
                    if receipt.authorization_id != row["authorization_id"]:
                        malformed += 1
            except (ValueError, TypeError):
                malformed += 1

        return {
            "ok": quick_ok and malformed == 0 and len(rows) <= MAX_FENCE_RECORDS,
            "sqlite_quick_check": "ok" if quick_ok else "failed",
            "records": len(rows),
            "capacity": MAX_FENCE_RECORDS,
            "semantic_integrity_errors": malformed,
            "indeterminate_records": sum(
                1
                for row in rows
                if row["state"] == SdaReleaseFenceState.INDETERMINATE.value
            ),
        }

    def _required_row(self, connection: sqlite3.Connection, authorization_id: str):
        row = connection.execute(
            "SELECT * FROM releases WHERE authorization_id=?",
            (authorization_id,),
        ).fetchone()
        if row is None:
            raise SdaReleaseFenceError("release authorization is not registered")
        return row

    def _assert_candidate(self, row: sqlite3.Row, observed_digest: str) -> None:
        if row["candidate_digest"] != observed_digest:
            raise SdaReleaseFenceConflict(
                "release candidate changed after durable verification"
            )

    def _assert_claim_token_and_owner(
        self,
        row: sqlite3.Row,
        owner: str,
        claim_token: str,
    ) -> None:
        if row["claim_owner"] != owner:
            raise SdaReleaseFenceConflict("release claim owner mismatch")
        if row["claim_token_sha256"] != _token_hash(claim_token):
            raise SdaReleaseFenceConflict("release claim token mismatch")

    def _assert_claim(
        self,
        row: sqlite3.Row,
        owner: str,
        claim_token: str,
        current: datetime,
    ) -> None:
        if SdaReleaseFenceState(row["state"]) != SdaReleaseFenceState.CLAIMED:
            raise SdaReleaseFenceConflict("release is not in CLAIMED state")
        self._assert_claim_token_and_owner(row, owner, claim_token)
        expiry = _parse_time(row["claim_expires_at"])
        if expiry is None or current >= expiry:
            raise SdaReleaseFenceConflict("release claim lease expired before invocation")

    def _transition(
        self,
        connection: sqlite3.Connection,
        authorization_id: str,
        from_state: SdaReleaseFenceState | None,
        to_state: SdaReleaseFenceState,
        occurred_at: datetime,
        actor: str,
        evidence_ref: str | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO transitions(
                authorization_id, from_state, to_state,
                occurred_at, actor, evidence_ref
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                authorization_id,
                None if from_state is None else from_state.value,
                to_state.value,
                _utc_text(occurred_at),
                actor,
                evidence_ref,
            ),
        )

    def _fetch_record(
        self,
        connection: sqlite3.Connection,
        authorization_id: str,
    ) -> SdaReleaseFenceRecord:
        row = self._required_row(connection, authorization_id)
        return self._row_to_record(row)

    def _row_to_record(self, row: sqlite3.Row) -> SdaReleaseFenceRecord:
        receipt = (
            None
            if not row["receipt_json"]
            else SdaReleaseReceipt.model_validate_json(row["receipt_json"])
        )
        return SdaReleaseFenceRecord(
            authorization_id=row["authorization_id"],
            state=SdaReleaseFenceState(row["state"]),
            candidate_digest=row["candidate_digest"],
            claim_owner=row["claim_owner"],
            claimed_at=_parse_time(row["claimed_at"]),
            claim_expires_at=_parse_time(row["claim_expires_at"]),
            invoking_at=_parse_time(row["invoking_at"]),
            finalized_at=_parse_time(row["finalized_at"]),
            attempt_count=row["attempt_count"],
            result_evidence_ref=row["result_evidence_ref"],
            receipt=receipt,
        )

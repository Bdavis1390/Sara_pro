#!/usr/bin/env python3
"""Durable replay and evidence-chain state for WS-QPHONON deployment.

SQLite is used as a local durable coordination primitive. Transactions are
fail-closed and use WAL + synchronous=FULL. This store does not authenticate
laboratory data; it prevents local replay and sequence rollback after restart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
from typing import Optional


ZERO_DIGEST = "0" * 64


@dataclass(frozen=True)
class StreamState:
    stream: str
    sequence: int
    event_digest: str


class DurableStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
            os.close(fd)
        os.chmod(self.path, 0o600)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consumed_ids (
                    kind TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    consumed_at_utc TEXT NOT NULL,
                    PRIMARY KEY (kind, identifier)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stream_state (
                    stream TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL CHECK(sequence >= 0),
                    event_digest TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL
                )
                """
            )

    def has_consumed(self, kind: str, identifier: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM consumed_ids WHERE kind = ? AND identifier = ?",
                (kind, identifier),
            ).fetchone()
        return row is not None

    def get_stream(self, stream: str) -> Optional[StreamState]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT sequence, event_digest FROM stream_state WHERE stream = ?",
                (stream,),
            ).fetchone()
        if row is None:
            return None
        return StreamState(stream=stream, sequence=int(row[0]), event_digest=str(row[1]))

    def consume_once(self, kind: str, identifier: str, payload_digest: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    INSERT INTO consumed_ids(kind, identifier, payload_digest, consumed_at_utc)
                    VALUES (?, ?, ?, ?)
                    """,
                    (kind, identifier, payload_digest, now),
                )
                conn.execute("COMMIT")
                return True
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def commit_event(
        self,
        *,
        stream: str,
        event_id: str,
        event_digest: str,
        sequence: int,
        previous_event_digest: str,
    ) -> tuple[bool, str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                duplicate = conn.execute(
                    "SELECT 1 FROM consumed_ids WHERE kind = 'event' AND identifier = ?",
                    (event_id,),
                ).fetchone()
                if duplicate is not None:
                    conn.execute("ROLLBACK")
                    return False, "EVENT_REPLAY_DETECTED"

                row = conn.execute(
                    "SELECT sequence, event_digest FROM stream_state WHERE stream = ?",
                    (stream,),
                ).fetchone()

                if row is None:
                    if sequence != 0 or previous_event_digest != ZERO_DIGEST:
                        conn.execute("ROLLBACK")
                        return False, "GENESIS_SEQUENCE_OR_DIGEST_INVALID"
                    conn.execute(
                        """
                        INSERT INTO stream_state(stream, sequence, event_digest, updated_at_utc)
                        VALUES (?, ?, ?, ?)
                        """,
                        (stream, sequence, event_digest, now),
                    )
                else:
                    current_sequence = int(row[0])
                    current_digest = str(row[1])
                    if sequence != current_sequence + 1:
                        conn.execute("ROLLBACK")
                        return False, "EVENT_SEQUENCE_NOT_MONOTONIC"
                    if previous_event_digest != current_digest:
                        conn.execute("ROLLBACK")
                        return False, "EVENT_CHAIN_MISMATCH"
                    conn.execute(
                        """
                        UPDATE stream_state
                        SET sequence = ?, event_digest = ?, updated_at_utc = ?
                        WHERE stream = ?
                        """,
                        (sequence, event_digest, now, stream),
                    )

                conn.execute(
                    """
                    INSERT INTO consumed_ids(kind, identifier, payload_digest, consumed_at_utc)
                    VALUES ('event', ?, ?, ?)
                    """,
                    (event_id, event_digest, now),
                )
                conn.execute("COMMIT")
                return True, "EVENT_COMMITTED"
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False, "EVENT_REPLAY_DETECTED"
            except Exception:
                conn.execute("ROLLBACK")
                raise

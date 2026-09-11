from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .echo_event_store import EchoEventStore, EchoEventStoreError, semantic_sha256
from .models import AuditRecord


CHECKPOINT_SCHEMA = "WS-ECHO-CHECKPOINT-V1"
CHECKPOINT_BUNDLE_SCHEMA = "WS-ECHO-CHECKPOINT-BUNDLE-V1"
CHECKPOINT_DB_SCHEMA = "WS-ECHO-CHECKPOINT-LEDGER-V1"
CHECKPOINT_PRIVATE_KEY_FILE_ENV = "ECHO_CHECKPOINT_PRIVATE_KEY_FILE"
CHECKPOINT_KEY_ID_ENV = "ECHO_CHECKPOINT_KEY_ID"
MAX_CHECKPOINT_KEY_FILE_BYTES = 16 * 1024
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class EchoCheckpointError(RuntimeError):
    pass


class EchoCheckpointConfigError(EchoCheckpointError):
    pass


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_private_key(path_value: str) -> Ed25519PrivateKey:
    if not path_value:
        raise EchoCheckpointConfigError(f"{CHECKPOINT_PRIVATE_KEY_FILE_ENV} is required")
    path = Path(path_value)
    if not path.is_absolute():
        raise EchoCheckpointConfigError(
            f"{CHECKPOINT_PRIVATE_KEY_FILE_ENV} must be an absolute path"
        )
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise EchoCheckpointConfigError("unable to inspect ECHO checkpoint private key") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise EchoCheckpointConfigError("ECHO checkpoint private key must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise EchoCheckpointConfigError("unable to open ECHO checkpoint private key securely") from exc
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise EchoCheckpointConfigError("ECHO checkpoint private key must be a regular file")
        if (link_status.st_dev, link_status.st_ino) != (status.st_dev, status.st_ino):
            raise EchoCheckpointConfigError("ECHO checkpoint private key changed during secure open")
        if status.st_uid != os.geteuid():
            raise EchoCheckpointConfigError("ECHO checkpoint private key must be owned by the service UID")
        if stat.S_IMODE(status.st_mode) & 0o077:
            raise EchoCheckpointConfigError(
                "ECHO checkpoint private key must not grant group/other permissions"
            )
        if status.st_size < 1 or status.st_size > MAX_CHECKPOINT_KEY_FILE_BYTES:
            raise EchoCheckpointConfigError("ECHO checkpoint private key size is invalid")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_CHECKPOINT_KEY_FILE_BYTES + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_CHECKPOINT_KEY_FILE_BYTES:
        raise EchoCheckpointConfigError("ECHO checkpoint private key is too large")
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (TypeError, ValueError) as exc:
        raise EchoCheckpointConfigError(
            "ECHO checkpoint private key must be an unencrypted PEM private key"
        ) from exc
    if not isinstance(key, Ed25519PrivateKey):
        raise EchoCheckpointConfigError("ECHO checkpoint private key must contain Ed25519 material")
    return key


def _load_key_id() -> str:
    value = os.getenv(CHECKPOINT_KEY_ID_ENV, "").strip()
    if not _KEY_ID_PATTERN.fullmatch(value):
        raise EchoCheckpointConfigError(
            f"{CHECKPOINT_KEY_ID_ENV} must be 1-128 safe identifier characters"
        )
    return value


def checkpoint_leaf_hash(event_id: str, semantic_digest: str) -> bytes:
    if not event_id or not _SHA256_PATTERN.fullmatch(semantic_digest):
        raise EchoCheckpointError("invalid checkpoint leaf")
    return hashlib.sha256(
        b"WS-ECHO-CHECKPOINT-LEAF-V1\0"
        + event_id.encode("utf-8")
        + b"\0"
        + semantic_digest.encode("ascii")
    ).digest()


def merkle_root(items: list[dict[str, Any]]) -> str:
    if not items:
        raise EchoCheckpointError("cannot checkpoint an empty ECHO event set")
    layer = [
        checkpoint_leaf_hash(str(item["event_id"]), str(item["semantic_sha256"]))
        for item in items
    ]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [
            hashlib.sha256(b"WS-ECHO-CHECKPOINT-NODE-V1\0" + layer[i] + layer[i + 1]).digest()
            for i in range(0, len(layer), 2)
        ]
    return layer[0].hex()


class EchoCheckpointManager:
    def __init__(
        self,
        store: EchoEventStore,
        *,
        private_key: Ed25519PrivateKey,
        key_id: str,
    ) -> None:
        self.store = store
        self._private_key = private_key
        self.key_id = key_id
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()
        self._initialize()

    @classmethod
    def from_environment(cls, store: EchoEventStore) -> "EchoCheckpointManager":
        return cls(
            store,
            private_key=_read_private_key(os.getenv(CHECKPOINT_PRIVATE_KEY_FILE_ENV, "")),
            key_id=_load_key_id(),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.store.db_path, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS echo_checkpoint_metadata (
                    name TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS echo_checkpoints (
                    sequence INTEGER PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    previous_checkpoint_sha256 TEXT,
                    checkpoint_sha256 TEXT NOT NULL UNIQUE,
                    merkle_root_sha256 TEXT NOT NULL,
                    event_count INTEGER NOT NULL CHECK(event_count > 0),
                    key_id TEXT NOT NULL,
                    key_fingerprint_sha256 TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    signature_b64url TEXT NOT NULL,
                    bundle_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS echo_checkpoint_events (
                    checkpoint_sequence INTEGER NOT NULL,
                    ordinal INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    semantic_sha256 TEXT NOT NULL,
                    PRIMARY KEY(checkpoint_sequence, ordinal),
                    UNIQUE(checkpoint_sequence, event_id),
                    FOREIGN KEY(checkpoint_sequence) REFERENCES echo_checkpoints(sequence)
                );
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO echo_checkpoint_metadata(name,value) VALUES('schema',?)",
                (CHECKPOINT_DB_SCHEMA,),
            )
            schema = connection.execute(
                "SELECT value FROM echo_checkpoint_metadata WHERE name='schema'"
            ).fetchone()
            if schema is None or schema["value"] != CHECKPOINT_DB_SCHEMA:
                raise EchoCheckpointError("ECHO checkpoint database schema mismatch")
            binding_name = f"checkpoint_key_fingerprint:{self.key_id}"
            row = connection.execute(
                "SELECT value FROM echo_checkpoint_metadata WHERE name=?", (binding_name,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO echo_checkpoint_metadata(name,value) VALUES(?,?)",
                    (binding_name, self.fingerprint_sha256),
                )
            elif row["value"] != self.fingerprint_sha256:
                raise EchoCheckpointConfigError(
                    "ECHO checkpoint key ID is already bound to different key material"
                )
            connection.commit()
        except (sqlite3.Error, EchoCheckpointError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def public_key_record(self) -> dict[str, str]:
        return {
            "schema": "WS-ECHO-CHECKPOINT-PUBLIC-KEY-V1",
            "issuer": "ECHO_SENTINEL_LINK",
            "purpose": "PROVENANCE_CHECKPOINT_SIGNING",
            "algorithm": "Ed25519",
            "key_id": self.key_id,
            "public_key_b64url": self.public_key_b64url,
            "fingerprint_sha256": self.fingerprint_sha256,
        }

    def _validated_current_items(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        rows = connection.execute(
            "SELECT event_id, semantic_sha256, event, actor, payload_json, first_audit_timestamp "
            "FROM events ORDER BY event_id"
        ).fetchall()
        items: list[dict[str, Any]] = []
        for ordinal, row in enumerate(rows, start=1):
            try:
                payload = json.loads(row["payload_json"])
                audit = AuditRecord(
                    timestamp=row["first_audit_timestamp"],
                    event=row["event"],
                    actor=row["actor"],
                    payload=payload,
                )
                digest = semantic_sha256(audit)
            except (ValueError, TypeError, json.JSONDecodeError, EchoEventStoreError) as exc:
                raise EchoCheckpointError("ECHO accepted event failed semantic validation") from exc
            if audit.payload.get("_outbox_event_id") != row["event_id"]:
                raise EchoCheckpointError("ECHO stable event ID does not match stored payload")
            if digest != row["semantic_sha256"]:
                raise EchoCheckpointError("ECHO semantic digest mismatch blocks checkpoint creation")
            items.append(
                {
                    "ordinal": ordinal,
                    "event_id": row["event_id"],
                    "semantic_sha256": digest,
                }
            )
        return items

    def create_checkpoint(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            quick = connection.execute("PRAGMA quick_check").fetchone()
            if quick is None or quick[0] != "ok":
                raise EchoCheckpointError("ECHO database integrity check failed")
            items = self._validated_current_items(connection)
            if not items:
                raise EchoCheckpointError("cannot checkpoint an empty ECHO event store")

            previous = connection.execute(
                "SELECT * FROM echo_checkpoints ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            sequence = 1 if previous is None else int(previous["sequence"]) + 1
            previous_digest = None if previous is None else str(previous["checkpoint_sha256"])
            if previous is not None:
                prior_rows = connection.execute(
                    "SELECT event_id, semantic_sha256 FROM echo_checkpoint_events "
                    "WHERE checkpoint_sequence=? ORDER BY ordinal",
                    (previous["sequence"],),
                ).fetchall()
                current = {str(item["event_id"]): str(item["semantic_sha256"]) for item in items}
                for prior in prior_rows:
                    if current.get(prior["event_id"]) != prior["semantic_sha256"]:
                        raise EchoCheckpointError(
                            "accepted provenance deletion or substitution blocks checkpoint creation"
                        )

            root = merkle_root(items)
            created_at = _utc_now()
            checkpoint_id = f"ECHO-CHK-{sequence:08d}-{root[:16]}"
            manifest = {
                "schema": CHECKPOINT_SCHEMA,
                "issuer": "ECHO_SENTINEL_LINK",
                "checkpoint_id": checkpoint_id,
                "sequence": sequence,
                "created_at": created_at,
                "previous_checkpoint_sha256": previous_digest,
                "event_count": len(items),
                "events": items,
                "merkle_root_sha256": root,
                "algorithm": "Ed25519",
                "key_id": self.key_id,
                "key_fingerprint_sha256": self.fingerprint_sha256,
                "claims_boundary": (
                    "Local signed checkpoint evidence only; no immutable/WORM retention, "
                    "external anchoring, third-party attestation, or exactly-once transport is claimed."
                ),
            }
            manifest_bytes = _canonical(manifest)
            checkpoint_digest = hashlib.sha256(manifest_bytes).hexdigest()
            signature = _b64url(self._private_key.sign(manifest_bytes))
            bundle = {
                "schema": CHECKPOINT_BUNDLE_SCHEMA,
                "manifest": manifest,
                "checkpoint_sha256": checkpoint_digest,
                "signature_b64url": signature,
                "public_key": self.public_key_record(),
            }
            manifest_json = _canonical(manifest).decode("utf-8")
            bundle_json = _canonical(bundle).decode("utf-8")
            connection.execute(
                """
                INSERT INTO echo_checkpoints(
                    sequence, checkpoint_id, created_at, previous_checkpoint_sha256,
                    checkpoint_sha256, merkle_root_sha256, event_count, key_id,
                    key_fingerprint_sha256, manifest_json, signature_b64url, bundle_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sequence,
                    checkpoint_id,
                    created_at,
                    previous_digest,
                    checkpoint_digest,
                    root,
                    len(items),
                    self.key_id,
                    self.fingerprint_sha256,
                    manifest_json,
                    signature,
                    bundle_json,
                ),
            )
            connection.executemany(
                """
                INSERT INTO echo_checkpoint_events(
                    checkpoint_sequence, ordinal, event_id, semantic_sha256
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (sequence, item["ordinal"], item["event_id"], item["semantic_sha256"])
                    for item in items
                ],
            )
            connection.commit()
            return bundle
        except (sqlite3.Error, EchoCheckpointError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def get_checkpoint(self, sequence: int) -> dict[str, Any] | None:
        if sequence < 1:
            raise EchoCheckpointError("checkpoint sequence must be >= 1")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT bundle_json FROM echo_checkpoints WHERE sequence=?", (sequence,)
            ).fetchone()
            if row is None:
                return None
            value = json.loads(row["bundle_json"])
            if not isinstance(value, dict):
                raise EchoCheckpointError("stored checkpoint bundle is not a JSON object")
            return value
        finally:
            connection.close()

    def latest_status(self) -> dict[str, Any]:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT sequence,checkpoint_id,checkpoint_sha256,event_count,created_at "
                "FROM echo_checkpoints ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            count = connection.execute("SELECT COUNT(*) FROM echo_checkpoints").fetchone()[0]
        finally:
            connection.close()
        if row is None:
            return {
                "checkpoint_count": 0,
                "latest_sequence": None,
                "latest_checkpoint_id": None,
                "latest_checkpoint_sha256": None,
                "latest_event_count": None,
                "latest_created_at": None,
            }
        return {
            "checkpoint_count": count,
            "latest_sequence": row["sequence"],
            "latest_checkpoint_id": row["checkpoint_id"],
            "latest_checkpoint_sha256": row["checkpoint_sha256"],
            "latest_event_count": row["event_count"],
            "latest_created_at": row["created_at"],
        }

from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from .echo_checkpoint_signer import (
    CHECKPOINT_SIGNATURE_CONTEXT,
    CheckpointSigner,
    Ed25519CheckpointSigner,
    EchoCheckpointSignerConfigError,
    MLDSA65CheckpointSigner,
    signer_from_environment,
)
from .echo_event_store import EchoEventStore, EchoEventStoreError, semantic_sha256
from .models import AuditRecord


CHECKPOINT_SCHEMA = "WS-ECHO-CHECKPOINT-V1"
CHECKPOINT_BUNDLE_SCHEMA = "WS-ECHO-CHECKPOINT-BUNDLE-V1"
CHECKPOINT_DB_SCHEMA = "WS-ECHO-CHECKPOINT-LEDGER-V1"
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
        private_key: Ed25519PrivateKey | MLDSA65PrivateKey | None = None,
        key_id: str | None = None,
        signer: CheckpointSigner | None = None,
    ) -> None:
        self.store = store
        if signer is not None and (private_key is not None or key_id is not None):
            raise EchoCheckpointConfigError(
                "provide either a checkpoint signer or private_key/key_id, not both"
            )
        if signer is None:
            if private_key is None or not key_id:
                raise EchoCheckpointConfigError("checkpoint private key and key ID are required")
            if isinstance(private_key, MLDSA65PrivateKey):
                signer = MLDSA65CheckpointSigner(private_key=private_key, key_id=key_id)
            elif isinstance(private_key, Ed25519PrivateKey):
                signer = Ed25519CheckpointSigner(private_key=private_key, key_id=key_id)
            else:
                raise EchoCheckpointConfigError("unsupported ECHO checkpoint private-key type")
        self._signer = signer
        self.key_id = signer.key_id
        self.algorithm = signer.algorithm
        self.public_key_b64url = signer.public_key_b64url
        self.fingerprint_sha256 = signer.fingerprint_sha256
        self._initialize()

    @classmethod
    def from_environment(cls, store: EchoEventStore) -> "EchoCheckpointManager":
        try:
            signer = signer_from_environment()
        except EchoCheckpointSignerConfigError as exc:
            raise EchoCheckpointConfigError(str(exc)) from exc
        return cls(store, signer=signer)

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
            algorithm_binding = f"checkpoint_key_algorithm:{self.key_id}"
            algorithm_row = connection.execute(
                "SELECT value FROM echo_checkpoint_metadata WHERE name=?", (algorithm_binding,)
            ).fetchone()
            if algorithm_row is None:
                connection.execute(
                    "INSERT INTO echo_checkpoint_metadata(name,value) VALUES(?,?)",
                    (algorithm_binding, self.algorithm),
                )
            elif algorithm_row["value"] != self.algorithm:
                raise EchoCheckpointConfigError(
                    "ECHO checkpoint key ID is already bound to a different signing algorithm"
                )
            connection.commit()
        except (sqlite3.Error, EchoCheckpointError):
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def public_key_record(self) -> dict[str, str]:
        return self._signer.public_key_record()

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
                "algorithm": self.algorithm,
                "key_id": self.key_id,
                "key_fingerprint_sha256": self.fingerprint_sha256,
                "claims_boundary": (
                    "Local signed checkpoint evidence only. ML-DSA-65 checkpoints provide "
                    "post-quantum signature protection for this checkpoint layer; immutable/WORM "
                    "retention, external anchoring, third-party attestation, transport PQ security, "
                    "and exactly-once transport are separate properties."
                    if self.algorithm == "ML-DSA-65"
                    else
                    "Legacy classical local signed checkpoint evidence only; this checkpoint is not "
                    "post-quantum signature protected."
                ),
            }
            if self.algorithm == "ML-DSA-65":
                manifest["signature_context"] = CHECKPOINT_SIGNATURE_CONTEXT.decode("ascii")
            manifest_bytes = _canonical(manifest)
            checkpoint_digest = hashlib.sha256(manifest_bytes).hexdigest()
            signature = _b64url(self._signer.sign(manifest_bytes))
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
                "algorithm": self.algorithm,
                "post_quantum_signature_protection": self.algorithm == "ML-DSA-65",
            }
        return {
            "checkpoint_count": count,
            "latest_sequence": row["sequence"],
            "latest_checkpoint_id": row["checkpoint_id"],
            "latest_checkpoint_sha256": row["checkpoint_sha256"],
            "latest_event_count": row["event_count"],
            "latest_created_at": row["created_at"],
            "algorithm": self.algorithm,
            "post_quantum_signature_protection": self.algorithm == "ML-DSA-65",
        }

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .echo_checkpoint import _read_private_key
from .limits import MAX_AUDIT_LINE_BYTES
from .models import AuditRecord
from .storage import DurableStore


AUDIT_CHECKPOINT_SCHEMA = "WS-SARA-AUDIT-CHECKPOINT-V1"
AUDIT_CHECKPOINT_BUNDLE_SCHEMA = "WS-SARA-AUDIT-CHECKPOINT-BUNDLE-V1"
AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA = "WS-SARA-AUDIT-CHECKPOINT-PUBLIC-KEY-V1"
AUDIT_CHECKPOINT_LEDGER_NAME = "audit-checkpoints.jsonl"
AUDIT_CHECKPOINT_KEY_FILE_ENV = "ECHO_CHECKPOINT_PRIVATE_KEY_FILE"
AUDIT_CHECKPOINT_KEY_ID_ENV = "ECHO_CHECKPOINT_KEY_ID"
MAX_CHECKPOINT_LINE_BYTES = 64 * 1024
_KEY_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SaraAuditCheckpointError(RuntimeError):
    pass


class SaraAuditCheckpointConfigError(SaraAuditCheckpointError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_key_id() -> str:
    value = os.getenv(AUDIT_CHECKPOINT_KEY_ID_ENV, "").strip()
    if not _KEY_ID_PATTERN.fullmatch(value):
        raise SaraAuditCheckpointConfigError(
            f"{AUDIT_CHECKPOINT_KEY_ID_ENV} must be 1-128 safe identifier characters"
        )
    return value


def audit_record_digest(value: dict[str, Any]) -> bytes:
    """Return the semantic digest of one canonical SARA application audit record."""
    if set(value) != {"timestamp", "event", "actor", "payload"}:
        raise SaraAuditCheckpointError("audit record shape mismatch")
    try:
        record = AuditRecord.model_validate(value)
    except Exception as exc:
        raise SaraAuditCheckpointError("audit record validation failed") from exc
    if not record.timestamp or not record.event or not record.actor:
        raise SaraAuditCheckpointError("audit record contains empty required text")
    normalized = record.model_dump(mode="json")
    return hashlib.sha256(
        b"WS-SARA-AUDIT-RECORD-V1\0" + _canonical(normalized)
    ).digest()


def audit_chain_step(previous: bytes, ordinal: int, record_digest: bytes) -> bytes:
    if len(previous) != 32 or len(record_digest) != 32 or ordinal < 1:
        raise SaraAuditCheckpointError("invalid audit chain step")
    return hashlib.sha256(
        b"WS-SARA-AUDIT-CHAIN-V1\0"
        + ordinal.to_bytes(8, "big", signed=False)
        + previous
        + record_digest
    ).digest()


def audit_chain_seed() -> bytes:
    return hashlib.sha256(b"WS-SARA-AUDIT-CHAIN-SEED-V1\0").digest()


class SaraAuditCheckpointManager:
    """Create signed checkpoints for the complete SARA audit prefix.

    The checkpoint is intentionally separate from ``audit.jsonl``.  A signed
    checkpoint commits to record content *and order* through ``record_count``.
    Verification can therefore detect mutation, deletion, insertion, or
    reordering inside that checkpointed prefix.  Records appended after the
    checkpoint are reported as an uncheckpointed tail rather than silently
    treated as protected.

    The local checkpoint ledger itself is not WORM storage.  Supplying a
    separately retained expected latest checkpoint digest converts silent
    local checkpoint-ledger rollback into an explicit verification failure.
    """

    def __init__(
        self,
        store: DurableStore,
        *,
        private_key: Ed25519PrivateKey,
        key_id: str,
    ) -> None:
        if not _KEY_ID_PATTERN.fullmatch(key_id):
            raise SaraAuditCheckpointConfigError("invalid SARA audit checkpoint key ID")
        self.store = store
        self.private_key = private_key
        self.key_id = key_id
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key_b64url = _b64url(public_bytes)
        self.fingerprint_sha256 = hashlib.sha256(public_bytes).hexdigest()
        self.ledger_path = self.store.root / AUDIT_CHECKPOINT_LEDGER_NAME
        self._checkpoint_lock = threading.RLock()
        if self.ledger_path.exists() or self.ledger_path.is_symlink():
            self._secure_existing_ledger()

    @classmethod
    def from_environment(cls, store: DurableStore) -> "SaraAuditCheckpointManager":
        # Reuse the already-hardened ECHO private-key loader and local key
        # configuration.  Signature domains/purposes remain distinct.
        private_key = _read_private_key(os.getenv(AUDIT_CHECKPOINT_KEY_FILE_ENV, ""))
        return cls(store, private_key=private_key, key_id=_load_key_id())

    def public_key_record(self) -> dict[str, str]:
        return {
            "schema": AUDIT_CHECKPOINT_PUBLIC_KEY_SCHEMA,
            "issuer": "SARA",
            "purpose": "APPLICATION_AUDIT_CHECKPOINT_SIGNING",
            "algorithm": "Ed25519",
            "key_id": self.key_id,
            "public_key_b64url": self.public_key_b64url,
            "fingerprint_sha256": self.fingerprint_sha256,
        }

    def _secure_existing_ledger(self) -> None:
        try:
            status = self.ledger_path.lstat()
        except OSError as exc:
            raise SaraAuditCheckpointError("unable to inspect audit checkpoint ledger") from exc
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            raise SaraAuditCheckpointError("audit checkpoint ledger must be a regular file")
        if status.st_uid != os.geteuid():
            raise SaraAuditCheckpointError("audit checkpoint ledger must be owned by service UID")
        try:
            self.ledger_path.chmod(0o600)
        except OSError as exc:
            raise SaraAuditCheckpointError("unable to secure audit checkpoint ledger") from exc
        if stat.S_IMODE(self.ledger_path.stat().st_mode) != 0o600:
            raise SaraAuditCheckpointError("audit checkpoint ledger must be mode 0600")

    def _scan_audit(self) -> tuple[int, str, str | None]:
        """Return record count, order-sensitive chain head, and last record digest."""
        try:
            self.store.audit_path.lstat()
        except FileNotFoundError:
            raise SaraAuditCheckpointError("cannot checkpoint an empty SARA audit")

        descriptor = self.store._open_read_descriptor(self.store.audit_path, "audit file")
        state = audit_chain_seed()
        count = 0
        last_digest: str | None = None
        with os.fdopen(descriptor, "rb") as handle:
            while True:
                raw = handle.readline(MAX_AUDIT_LINE_BYTES + 2)
                if not raw:
                    break
                if len(raw) > MAX_AUDIT_LINE_BYTES + 1:
                    raise SaraAuditCheckpointError("audit record exceeds configured line limit")
                if raw.endswith(b"\n"):
                    raw = raw[:-1]
                if not raw:
                    raise SaraAuditCheckpointError("audit contains an empty record")
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise SaraAuditCheckpointError("audit contains invalid JSON") from exc
                if not isinstance(value, dict):
                    raise SaraAuditCheckpointError("audit record must be a JSON object")
                digest = audit_record_digest(value)
                count += 1
                state = audit_chain_step(state, count, digest)
                last_digest = digest.hex()
        if count < 1:
            raise SaraAuditCheckpointError("cannot checkpoint an empty SARA audit")
        return count, state.hex(), last_digest

    def _read_ledger(self) -> list[dict[str, Any]]:
        if not self.ledger_path.exists():
            return []
        self._secure_existing_ledger()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(self.ledger_path, flags)
        except OSError as exc:
            raise SaraAuditCheckpointError("unable to read audit checkpoint ledger") from exc
        bundles: list[dict[str, Any]] = []
        with os.fdopen(descriptor, "rb") as handle:
            while True:
                raw = handle.readline(MAX_CHECKPOINT_LINE_BYTES + 2)
                if not raw:
                    break
                if len(raw) > MAX_CHECKPOINT_LINE_BYTES + 1:
                    raise SaraAuditCheckpointError("audit checkpoint ledger line is too large")
                if raw.endswith(b"\n"):
                    raw = raw[:-1]
                if not raw:
                    raise SaraAuditCheckpointError("audit checkpoint ledger contains an empty line")
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise SaraAuditCheckpointError("audit checkpoint ledger contains invalid JSON") from exc
                if not isinstance(value, dict):
                    raise SaraAuditCheckpointError("audit checkpoint bundle must be a JSON object")
                bundles.append(value)
        return bundles

    def _append_bundle(self, bundle: dict[str, Any]) -> None:
        payload = _canonical(bundle) + b"\n"
        if len(payload) > MAX_CHECKPOINT_LINE_BYTES:
            raise SaraAuditCheckpointError("audit checkpoint bundle exceeds line limit")
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_APPEND
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(self.ledger_path, flags, 0o600)
        except OSError as exc:
            raise SaraAuditCheckpointError("unable to open audit checkpoint ledger") from exc
        try:
            status = os.fstat(descriptor)
            if not stat.S_ISREG(status.st_mode):
                raise SaraAuditCheckpointError("audit checkpoint ledger must be a regular file")
            os.fchmod(descriptor, 0o600)
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("checkpoint ledger write made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
        except OSError as exc:
            raise SaraAuditCheckpointError("unable to durably append audit checkpoint") from exc
        finally:
            os.close(descriptor)
        self._secure_existing_ledger()

    def create_checkpoint(self) -> dict[str, Any]:
        from .audit_checkpoint_verify import verify_checkpoint_chain

        with self._checkpoint_lock, self.store._lock:
            existing = self._read_ledger()
            previous_digest: str | None = None
            sequence = 1
            if existing:
                verified = verify_checkpoint_chain(existing, self.fingerprint_sha256)
                if verified["key_id"] != self.key_id:
                    raise SaraAuditCheckpointError("audit checkpoint key ID changed")
                previous_digest = verified["last_checkpoint_sha256"]
                sequence = int(verified["last_sequence"]) + 1

            record_count, chain_head, last_record_digest = self._scan_audit()
            if existing:
                prior_count = int(existing[-1]["manifest"]["record_count"])
                if record_count < prior_count:
                    raise SaraAuditCheckpointError(
                        "SARA audit is shorter than the previous signed checkpoint"
                    )

            created_at = _utc_now()
            checkpoint_id = f"SARA-AUDIT-CHK-{sequence:08d}-{chain_head[:16]}"
            manifest = {
                "schema": AUDIT_CHECKPOINT_SCHEMA,
                "issuer": "SARA",
                "purpose": "APPLICATION_AUDIT_PREFIX_INTEGRITY",
                "checkpoint_id": checkpoint_id,
                "sequence": sequence,
                "created_at": created_at,
                "previous_checkpoint_sha256": previous_digest,
                "record_count": record_count,
                "audit_chain_head_sha256": chain_head,
                "last_record_sha256": last_record_digest,
                "algorithm": "Ed25519",
                "key_id": self.key_id,
                "key_fingerprint_sha256": self.fingerprint_sha256,
                "claims_boundary": (
                    "Signed integrity evidence for the checkpointed local SARA audit prefix only; "
                    "uncheckpointed tail records, privileged deletion/rollback of both local log and "
                    "checkpoint ledger, signing-key compromise, WORM retention, external anchoring, "
                    "and third-party attestation are not established."
                ),
            }
            manifest_bytes = _canonical(manifest)
            checkpoint_digest = hashlib.sha256(manifest_bytes).hexdigest()
            signature = _b64url(self.private_key.sign(manifest_bytes))
            bundle = {
                "schema": AUDIT_CHECKPOINT_BUNDLE_SCHEMA,
                "manifest": manifest,
                "checkpoint_sha256": checkpoint_digest,
                "signature_b64url": signature,
                "public_key": self.public_key_record(),
            }
            self._append_bundle(bundle)
            return bundle

    def verify_current(
        self,
        *,
        expected_latest_checkpoint_sha256: str | None = None,
    ) -> dict[str, Any]:
        from .audit_checkpoint_verify import verify_checkpoint_chain

        with self._checkpoint_lock, self.store._lock:
            bundles = self._read_ledger()
            if not bundles:
                return {
                    "schema": "WS-SARA-AUDIT-INTEGRITY-STATUS-V1",
                    "status": "NO_CHECKPOINT",
                    "checkpoint_count": 0,
                    "claims_boundary": "No signed SARA application-audit checkpoint exists yet.",
                }
            chain = verify_checkpoint_chain(
                bundles,
                self.fingerprint_sha256,
                expected_latest_checkpoint_sha256=expected_latest_checkpoint_sha256,
            )
            current_count, current_head, _last = self._scan_audit()
            latest = bundles[-1]["manifest"]
            checkpointed_count = int(latest["record_count"])
            if current_count < checkpointed_count:
                raise SaraAuditCheckpointError(
                    "SARA audit truncation detected relative to signed checkpoint"
                )

            # Recompute exactly the signed prefix when newer records exist.
            if current_count == checkpointed_count:
                prefix_head = current_head
            else:
                prefix_head = self._scan_audit_prefix(checkpointed_count)
            if prefix_head != latest["audit_chain_head_sha256"]:
                raise SaraAuditCheckpointError(
                    "SARA audit checkpointed prefix integrity mismatch"
                )
            status = "PASS" if current_count == checkpointed_count else "PASS_WITH_UNCHECKPOINTED_TAIL"
            return {
                "schema": "WS-SARA-AUDIT-INTEGRITY-STATUS-V1",
                "status": status,
                "checkpoint_count": chain["checkpoint_count"],
                "latest_sequence": chain["last_sequence"],
                "latest_checkpoint_sha256": chain["last_checkpoint_sha256"],
                "checkpointed_records": checkpointed_count,
                "current_records": current_count,
                "uncheckpointed_records": current_count - checkpointed_count,
                "key_id": chain["key_id"],
                "key_fingerprint_sha256": self.fingerprint_sha256,
                "claims_boundary": (
                    "Cryptographic verification of the supplied/local signed checkpoint chain and "
                    "checkpointed SARA audit prefix only; external anchoring and privileged rollback "
                    "resistance require a separately retained expected latest checkpoint digest."
                ),
            }

    def _scan_audit_prefix(self, record_limit: int) -> str:
        if record_limit < 1:
            raise SaraAuditCheckpointError("audit prefix limit must be positive")
        descriptor = self.store._open_read_descriptor(self.store.audit_path, "audit file")
        state = audit_chain_seed()
        count = 0
        with os.fdopen(descriptor, "rb") as handle:
            while count < record_limit:
                raw = handle.readline(MAX_AUDIT_LINE_BYTES + 2)
                if not raw:
                    raise SaraAuditCheckpointError("audit ended inside checkpointed prefix")
                if len(raw) > MAX_AUDIT_LINE_BYTES + 1:
                    raise SaraAuditCheckpointError("audit record exceeds configured line limit")
                if raw.endswith(b"\n"):
                    raw = raw[:-1]
                if not raw:
                    raise SaraAuditCheckpointError("audit contains an empty record")
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise SaraAuditCheckpointError("audit contains invalid JSON") from exc
                if not isinstance(value, dict):
                    raise SaraAuditCheckpointError("audit record must be a JSON object")
                digest = audit_record_digest(value)
                count += 1
                state = audit_chain_step(state, count, digest)
        return state.hex()

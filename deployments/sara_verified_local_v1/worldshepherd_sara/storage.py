from __future__ import annotations

import json
import os
import secrets
import stat
import threading
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX platforms.
    fcntl = None  # type: ignore[assignment]

from .limits import MAX_AUDIT_LINE_BYTES, validate_json_resource
from .models import AuditRecord
from .registry_checkpoint import (
    REGISTRY_CHECKPOINT_META_KEY,
    RegistryCheckpointIntegrityError,
    VerifiedCheckpointJournal,
    canonical_json_bytes,
    checkpoint_metadata,
    make_genesis_record,
    make_transaction_records,
    parse_checkpoint_metadata,
    plan_checkpoint_recovery,
    registry_state_root_sha256,
    verify_checkpoint_journal,
)


T = TypeVar("T")
RegistryTransaction = Callable[
    [dict[str, Any]],
    tuple[dict[str, Any] | None, T],
]

MAX_CHECKPOINT_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_CHECKPOINT_LINE_BYTES = 16 * 1024


class DurableStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._secure_mode(root, 0o700, "data directory")
        self.root = root
        self.audit_path = root / "audit.jsonl"
        self.registry_path = root / "registry.json"
        self.registry_lock_path = root / "registry.lock"
        self.registry_checkpoint_path = root / "registry.checkpoints.jsonl"
        self._lock = threading.RLock()

        # Create and secure the lock inode before consulting or creating the
        # registry so two processes constructing DurableStore against the same
        # data directory cannot race registry initialization or checkpoint
        # recovery on POSIX.
        self._ensure_registry_lock_file()
        with self._lock:
            with self._registry_process_lock(exclusive=True):
                if not self.registry_path.exists():
                    self._atomic_write_json(self.registry_path, {})
                else:
                    self._secure_mode(self.registry_path, 0o600, "registry file")
                self._initialize_or_recover_checkpoint_unlocked()
        if self.audit_path.exists():
            self._secure_mode(self.audit_path, 0o600, "audit file")

    @property
    def registry_cross_process_lock_supported(self) -> bool:
        """Whether this runtime can enforce the POSIX advisory registry lock."""

        return fcntl is not None

    @staticmethod
    def _secure_mode(path: Path, mode: int, label: str) -> None:
        expected_directory = "directory" in label
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        if expected_directory:
            flags |= getattr(os, "O_DIRECTORY", 0)

        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise RuntimeError(f"Unable to secure {label}: {exc}") from exc

        try:
            path_status = os.fstat(descriptor)
            expected_type = stat.S_ISDIR if expected_directory else stat.S_ISREG

            if not expected_type(path_status.st_mode):
                raise RuntimeError(
                    f"Unable to secure {label}: unexpected file type"
                )

            os.fchmod(descriptor, mode)
            actual = stat.S_IMODE(os.fstat(descriptor).st_mode)

            if actual != mode:
                raise RuntimeError(
                    f"Unable to secure {label}: "
                    f"expected {mode:04o}, found {actual:04o}"
                )
        except OSError as exc:
            raise RuntimeError(f"Unable to secure {label}: {exc}") from exc
        finally:
            os.close(descriptor)

    def _ensure_registry_lock_file(self) -> None:
        flags = (
            os.O_RDWR
            | os.O_CREAT
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(self.registry_lock_path, flags, 0o600)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to create secured registry lock file: {exc}"
            ) from exc
        try:
            self._secure_descriptor(descriptor, 0o600, "registry lock file")
        finally:
            os.close(descriptor)
        self._secure_mode(self.registry_lock_path, 0o600, "registry lock file")

    @contextmanager
    def _registry_process_lock(self, *, exclusive: bool) -> Iterator[None]:
        """Hold a process-visible advisory lock around registry access on POSIX.

        On non-POSIX Python builds where ``fcntl`` is unavailable, the existing
        in-process ``RLock`` remains the only serialization primitive. Callers
        must consult ``registry_cross_process_lock_supported`` before claiming
        cross-process transaction semantics on such platforms.
        """

        if fcntl is None:
            yield
            return

        flags = (
            os.O_RDWR
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(self.registry_lock_path, flags)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to open registry lock file securely: {exc}"
            ) from exc

        try:
            self._secure_descriptor(descriptor, 0o600, "registry lock file")
            operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            try:
                fcntl.flock(descriptor, operation)
            except OSError as exc:
                raise RuntimeError(
                    f"Unable to acquire registry process lock: {exc}"
                ) from exc
            try:
                yield
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                except OSError as exc:
                    raise RuntimeError(
                        f"Unable to release registry process lock: {exc}"
                    ) from exc
        finally:
            os.close(descriptor)

    def _atomic_write_json(self, path: Path, value: Any) -> None:
        temp = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            descriptor = os.open(
                temp,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
        except OSError as exc:
            raise RuntimeError(f"Unable to create secured registry file: {exc}") from exc
        try:
            self._secure_descriptor(descriptor, 0o600, "temporary registry file")
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, sort_keys=True, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._secure_mode(temp, 0o600, "temporary registry file")
            os.replace(temp, path)
            self._secure_mode(path, 0o600, "registry file")
            self._fsync_directory(path.parent)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temp.unlink(missing_ok=True)
            raise

    @staticmethod
    def _secure_descriptor(descriptor: int, mode: int, label: str) -> None:
        try:
            file_status = os.fstat(descriptor)
            if not stat.S_ISREG(file_status.st_mode):
                raise RuntimeError(
                    f"Unable to secure {label}: unexpected file type"
                )

            os.fchmod(descriptor, mode)
            actual = stat.S_IMODE(os.fstat(descriptor).st_mode)
        except OSError as exc:
            raise RuntimeError(f"Unable to secure {label}: {exc}") from exc

        if actual != mode:
            raise RuntimeError(
                f"Unable to secure {label}: "
                f"expected {mode:04o}, found {actual:04o}"
            )

    @staticmethod
    def _open_read_descriptor(path: Path, label: str) -> int:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)

        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to open {label} securely: {exc}"
            ) from exc

        try:
            DurableStore._secure_descriptor(descriptor, 0o600, label)
        except Exception:
            os.close(descriptor)
            raise

        return descriptor

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )

        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to open registry directory securely: {exc}"
            ) from exc

        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise RuntimeError(
                    "Unable to secure registry directory: unexpected file type"
                )
            os.fsync(descriptor)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to synchronize registry directory: {exc}"
            ) from exc
        finally:
            os.close(descriptor)

    def _append_checkpoint_record_unlocked(self, record: dict[str, Any]) -> None:
        line = canonical_json_bytes(record) + b"\n"
        if len(line) > MAX_CHECKPOINT_LINE_BYTES:
            raise RegistryCheckpointIntegrityError(
                "checkpoint journal record exceeds line-size limit"
            )

        existed = self.registry_checkpoint_path.exists()
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_APPEND
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            descriptor = os.open(self.registry_checkpoint_path, flags, 0o600)
        except OSError as exc:
            raise RegistryCheckpointIntegrityError(
                f"unable to open checkpoint journal securely: {exc}"
            ) from exc
        try:
            self._secure_descriptor(descriptor, 0o600, "registry checkpoint journal")
            current_size = os.fstat(descriptor).st_size
            if current_size + len(line) > MAX_CHECKPOINT_JOURNAL_BYTES:
                raise RegistryCheckpointIntegrityError(
                    "checkpoint journal capacity exceeded"
                )
            written = os.write(descriptor, line)
            if written != len(line):
                raise RegistryCheckpointIntegrityError(
                    "short write while appending checkpoint journal"
                )
            os.fsync(descriptor)
        except OSError as exc:
            raise RegistryCheckpointIntegrityError(
                f"unable to append checkpoint journal: {exc}"
            ) from exc
        finally:
            os.close(descriptor)
        self._secure_mode(
            self.registry_checkpoint_path,
            0o600,
            "registry checkpoint journal",
        )
        if not existed:
            self._fsync_directory(self.registry_checkpoint_path.parent)

    def _read_checkpoint_records_unlocked(self) -> list[dict[str, Any]]:
        try:
            self.registry_checkpoint_path.lstat()
        except FileNotFoundError:
            return []
        descriptor = self._open_read_descriptor(
            self.registry_checkpoint_path,
            "registry checkpoint journal",
        )
        records: list[dict[str, Any]] = []
        try:
            size = os.fstat(descriptor).st_size
            if size > MAX_CHECKPOINT_JOURNAL_BYTES:
                raise RegistryCheckpointIntegrityError(
                    "checkpoint journal exceeds capacity limit"
                )
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                for raw_line in handle:
                    if len(raw_line) > MAX_CHECKPOINT_LINE_BYTES:
                        raise RegistryCheckpointIntegrityError(
                            "checkpoint journal line exceeds size limit"
                        )
                    if not raw_line.endswith(b"\n"):
                        raise RegistryCheckpointIntegrityError(
                            "checkpoint journal has an incomplete trailing record"
                        )
                    payload = raw_line[:-1]
                    if not payload:
                        raise RegistryCheckpointIntegrityError(
                            "checkpoint journal contains an empty record"
                        )
                    try:
                        parsed = json.loads(payload.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise RegistryCheckpointIntegrityError(
                            "checkpoint journal contains invalid JSON"
                        ) from exc
                    if not isinstance(parsed, dict):
                        raise RegistryCheckpointIntegrityError(
                            "checkpoint journal record is not an object"
                        )
                    records.append(parsed)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return records

    def _bootstrap_checkpoint_unlocked(
        self,
        registry: dict[str, Any],
        records: list[dict[str, Any]],
    ) -> None:
        metadata = parse_checkpoint_metadata(registry)
        if metadata is not None:
            if not records:
                raise RegistryCheckpointIntegrityError(
                    "checkpoint journal is missing for checkpointed registry"
                )
            return

        if not records:
            genesis = make_genesis_record(registry)
            self._append_checkpoint_record_unlocked(genesis)
            records = [genesis]
        else:
            journal = verify_checkpoint_journal(records)
            if (
                len(records) != 1
                or records[0]["record_type"] != "GENESIS"
                or journal.pending_prepare is not None
            ):
                raise RegistryCheckpointIntegrityError(
                    "registry metadata is missing but checkpoint history is not a recoverable genesis"
                )
            genesis = records[0]
            if registry_state_root_sha256(registry) != genesis["new_state_root_sha256"]:
                raise RegistryCheckpointIntegrityError(
                    "registry state does not match recoverable checkpoint genesis"
                )

        genesis = records[0]
        bootstrapped = dict(registry)
        bootstrapped[REGISTRY_CHECKPOINT_META_KEY] = checkpoint_metadata(
            generation=0,
            commit_hash=genesis["record_hash"],
            state_root_sha256=genesis["new_state_root_sha256"],
        )
        validate_json_resource(bootstrapped)
        self._atomic_write_json(self.registry_path, bootstrapped)

    def _initialize_or_recover_checkpoint_unlocked(self) -> None:
        registry = self._get_registry_unlocked()
        records = self._read_checkpoint_records_unlocked()
        self._bootstrap_checkpoint_unlocked(registry, records)

        registry = self._get_registry_unlocked()
        records = self._read_checkpoint_records_unlocked()
        if not records:
            raise RegistryCheckpointIntegrityError("checkpoint journal is missing")
        plan = plan_checkpoint_recovery(registry, records)
        if plan.action in {"RECOVER_COMMIT", "RECOVER_ABORT"}:
            assert plan.recovery_record is not None
            self._append_checkpoint_record_unlocked(plan.recovery_record)
            records = self._read_checkpoint_records_unlocked()
            final = plan_checkpoint_recovery(registry, records)
            if final.action != "HEALTHY":
                raise RegistryCheckpointIntegrityError(
                    "checkpoint recovery did not reach healthy state"
                )

    def _verified_registry_unlocked(
        self,
    ) -> tuple[dict[str, Any], VerifiedCheckpointJournal]:
        self._initialize_or_recover_checkpoint_unlocked()
        registry = self._get_registry_unlocked()
        records = self._read_checkpoint_records_unlocked()
        plan = plan_checkpoint_recovery(registry, records)
        if plan.action != "HEALTHY":
            raise RegistryCheckpointIntegrityError(
                "checkpoint recovery remains unresolved"
            )
        return registry, plan.journal

    def _checkpointed_registry_write_unlocked(
        self,
        current: dict[str, Any],
        updated: dict[str, Any],
        journal: VerifiedCheckpointJournal,
    ) -> dict[str, Any]:
        prepare, commit, final_registry = make_transaction_records(
            current,
            updated,
            journal=journal,
        )
        validate_json_resource(final_registry)

        # PREPARE is durable before registry replacement. The final registry
        # commits to the deterministic COMMIT hash before that COMMIT record is
        # appended. Startup/access recovery can therefore distinguish a write
        # that never applied from one whose registry replacement applied but
        # whose final journal append was interrupted.
        self._append_checkpoint_record_unlocked(prepare)
        self._atomic_write_json(self.registry_path, final_registry)
        self._append_checkpoint_record_unlocked(commit)
        return final_registry

    def append_audit(self, record: AuditRecord) -> None:
        line = record.model_dump_json(exclude_none=True)
        with self._lock:
            descriptor = os.open(
                self.audit_path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_APPEND
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                self._secure_descriptor(descriptor, 0o600, "audit file")
            except Exception:
                os.close(descriptor)
                raise
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._secure_mode(self.audit_path, 0o600, "audit file")

    def read_audit(self, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            try:
                self.audit_path.lstat()
            except FileNotFoundError:
                return []
            lines = self._bounded_tail(limit)
        records: list[dict[str, Any]] = []
        for line, truncated in lines:
            if truncated:
                records.append({"event": "audit_corruption_detected", "reason": "line_too_long"})
                continue
            try:
                value = json.loads(line.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("audit record is not an object")
                records.append(value)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                records.append({"event": "audit_corruption_detected", "reason": "invalid_line"})
        return records

    def _bounded_tail(self, limit: int) -> list[tuple[bytes, bool]]:
        records: deque[tuple[bytes, bool]] = deque(maxlen=limit)
        current = bytearray()
        truncated = False
        descriptor = self._open_read_descriptor(
            self.audit_path, "audit file"
        )
        with os.fdopen(descriptor, "rb") as handle:
            while chunk := handle.read(8192):
                for byte in chunk:
                    if byte == 0x0A:
                        records.append((bytes(current), truncated))
                        current.clear()
                        truncated = False
                    elif len(current) < MAX_AUDIT_LINE_BYTES:
                        current.append(byte)
                    else:
                        truncated = True
            if current or truncated:
                records.append((bytes(current), truncated))
        return list(records)

    def _get_registry_unlocked(self) -> dict[str, Any]:
        descriptor = self._open_read_descriptor(
            self.registry_path, "registry file"
        )
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            value = json.load(handle)

        if not isinstance(value, dict):
            raise ValueError("registry must contain a JSON object")

        return validate_json_resource(value)

    def get_registry(self) -> dict[str, Any]:
        # Reads take the exclusive process lock in MAG-1.5 because they may need
        # to complete deterministic recovery of a durable PREPARE left by a
        # crashed writer before returning security-sensitive state.
        with self._lock:
            with self._registry_process_lock(exclusive=True):
                registry, _journal = self._verified_registry_unlocked()
                return registry

    def patch_registry(self, values: dict[str, Any]) -> dict[str, Any]:
        if REGISTRY_CHECKPOINT_META_KEY in values:
            raise RegistryCheckpointIntegrityError(
                f"{REGISTRY_CHECKPOINT_META_KEY} is storage-owned metadata"
            )
        with self._lock:
            with self._registry_process_lock(exclusive=True):
                current, journal = self._verified_registry_unlocked()
                updated = dict(current)
                updated.update(values)
                validate_json_resource(updated)
                return self._checkpointed_registry_write_unlocked(
                    current,
                    updated,
                    journal,
                )

    def transact_registry(self, operation: RegistryTransaction[T]) -> T:
        """Execute a registry read/derive/write operation under one transaction lock.

        MAG-1.5 first verifies/reconciles the hash-chained checkpoint journal
        against the durable registry. If the callback returns a patch, PREPARE
        is fsynced before registry replacement and deterministic COMMIT is
        fsynced afterward. The registry itself carries storage-owned generation,
        state-root, and last-commit metadata. Restoring an older registry while
        retaining newer checkpoint history therefore fails closed.

        The callback receives the latest validated registry snapshot while the
        store's in-process lock and, on POSIX, the process-visible advisory
        registry lock are held. It returns a top-level patch (or ``None`` for a
        read/decision-only transaction) plus an arbitrary result. Exceptions
        before PREPARE abort without a write; interrupted writes after PREPARE
        are deterministically classified/recovered on the next protected access.

        This remains a local integrity mechanism. If a privileged actor rolls
        back or deletes both the registry and its checkpoint journal together,
        local state alone cannot prove that history was removed. External
        witnessing is a separate, stronger property.
        """
        with self._lock:
            with self._registry_process_lock(exclusive=True):
                current, journal = self._verified_registry_unlocked()
                original_checkpoint = dict(current[REGISTRY_CHECKPOINT_META_KEY])
                patch, result = operation(current)
                if current.get(REGISTRY_CHECKPOINT_META_KEY) != original_checkpoint:
                    raise RegistryCheckpointIntegrityError(
                        "registry transaction mutated storage-owned checkpoint metadata"
                    )
                if patch is None:
                    return result
                if not isinstance(patch, dict):
                    raise TypeError("registry transaction patch must be a dict or None")
                if REGISTRY_CHECKPOINT_META_KEY in patch:
                    raise RegistryCheckpointIntegrityError(
                        f"{REGISTRY_CHECKPOINT_META_KEY} is storage-owned metadata"
                    )
                updated = dict(current)
                updated.update(patch)
                validate_json_resource(updated)
                self._checkpointed_registry_write_unlocked(
                    current,
                    updated,
                    journal,
                )
                return result

    def checkpoint_status(self) -> dict[str, Any]:
        """Return the current locally verified checkpoint receipt."""

        with self._lock:
            with self._registry_process_lock(exclusive=True):
                registry, journal = self._verified_registry_unlocked()
                metadata = parse_checkpoint_metadata(registry)
                assert metadata is not None
                return {
                    "schema": metadata["schema"],
                    "generation": metadata["generation"],
                    "state_root_sha256": metadata["state_root_sha256"],
                    "commit_hash": metadata["commit_hash"],
                    "journal_tail_record_hash": journal.tail_record_hash,
                    "journal_tail_sequence": journal.tail_sequence,
                    "integrity_model": "LOCAL_HASH_CHAINED_REGISTRY_CHECKPOINT_V1",
                    "external_witnessed": False,
                }

    def check_storage(self) -> tuple[bool, str]:
        probe = self.root / f".readiness-{secrets.token_hex(8)}"
        try:
            self._secure_mode(self.root, 0o700, "data directory")
            self._secure_mode(self.registry_lock_path, 0o600, "registry lock file")
            self._secure_mode(self.registry_path, 0o600, "registry file")
            self._secure_mode(
                self.registry_checkpoint_path,
                0o600,
                "registry checkpoint journal",
            )
            self.get_registry()
            descriptor = os.open(
                probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write("ready\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._secure_mode(probe, 0o600, "readiness probe")
            probe.unlink()
        except (
            OSError,
            RuntimeError,
            RegistryCheckpointIntegrityError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
            return False, str(exc)
        return True, "persistent storage and registry checkpoint integrity are verified"

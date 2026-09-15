from __future__ import annotations

import json
import math
import os
import secrets
import stat
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from .limits import MAX_AUDIT_LINE_BYTES, validate_json_resource
from .models import AuditRecord


T = TypeVar("T")
RegistryTransaction = Callable[
    [dict[str, Any]],
    tuple[dict[str, Any] | None, T],
]
MAX_AUDIT_GROUP_COMMIT_BATCH = 64
MAX_AUDIT_GROUP_COMMIT_WINDOW_MS = 10.0


class _AuditAppendWaiter:
    def __init__(self, line: str) -> None:
        self.line = line
        self.done = threading.Event()
        self.error: Exception | None = None


class DurableStore:
    def __init__(
        self,
        data_dir: str | Path | None = None,
        *,
        audit_group_commit: bool | None = None,
        audit_group_commit_window_ms: float | None = None,
    ) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._secure_mode(root, 0o700, "data directory")
        self.root = root
        self.audit_path = root / "audit.jsonl"
        self.registry_path = root / "registry.json"
        self._lock = threading.RLock()

        if audit_group_commit is None:
            audit_group_commit = os.getenv("SARA_AUDIT_GROUP_COMMIT", "0") == "1"
        if audit_group_commit_window_ms is None:
            raw_window = os.getenv("SARA_AUDIT_GROUP_COMMIT_WINDOW_MS", "0.5")
            try:
                audit_group_commit_window_ms = float(raw_window)
            except ValueError as exc:
                raise ValueError(
                    "SARA_AUDIT_GROUP_COMMIT_WINDOW_MS must be numeric"
                ) from exc
        if (
            not math.isfinite(audit_group_commit_window_ms)
            or audit_group_commit_window_ms < 0.0
            or audit_group_commit_window_ms > MAX_AUDIT_GROUP_COMMIT_WINDOW_MS
        ):
            raise ValueError(
                "audit_group_commit_window_ms must be finite and between "
                f"0 and {MAX_AUDIT_GROUP_COMMIT_WINDOW_MS} ms"
            )
        self.audit_group_commit_enabled = bool(audit_group_commit)
        self.audit_group_commit_window_ms = float(audit_group_commit_window_ms)
        self._audit_group_condition = threading.Condition(threading.Lock())
        self._audit_group_pending: list[_AuditAppendWaiter] = []
        self._audit_group_leader_active = False

        if not self.registry_path.exists():
            self._atomic_write_json(self.registry_path, {})
        else:
            self._secure_mode(self.registry_path, 0o600, "registry file")
        if self.audit_path.exists():
            self._secure_mode(self.audit_path, 0o600, "audit file")

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

    def append_audit(self, record: AuditRecord) -> None:
        line = record.model_dump_json(exclude_none=True)
        if not self.audit_group_commit_enabled:
            self._write_audit_lines([line])
            return
        self._append_audit_group_commit(line)

    def _write_audit_lines(self, lines: list[str]) -> None:
        if not lines:
            return
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
                for line in lines:
                    handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._secure_mode(self.audit_path, 0o600, "audit file")

    def _append_audit_group_commit(self, line: str) -> None:
        waiter = _AuditAppendWaiter(line)
        leader = False
        with self._audit_group_condition:
            self._audit_group_pending.append(waiter)
            if not self._audit_group_leader_active:
                self._audit_group_leader_active = True
                leader = True

        if leader:
            self._drain_audit_group_commit()

        waiter.done.wait()
        if waiter.error is not None:
            raise RuntimeError("Grouped audit append failed before durability") from waiter.error

    def _drain_audit_group_commit(self) -> None:
        if self.audit_group_commit_window_ms > 0.0:
            time.sleep(self.audit_group_commit_window_ms / 1000.0)

        while True:
            with self._audit_group_condition:
                if not self._audit_group_pending:
                    self._audit_group_leader_active = False
                    return
                batch = self._audit_group_pending[:MAX_AUDIT_GROUP_COMMIT_BATCH]
                del self._audit_group_pending[: len(batch)]

            error: Exception | None = None
            try:
                self._write_audit_lines([waiter.line for waiter in batch])
            except Exception as exc:
                error = exc

            for waiter in batch:
                waiter.error = error
                waiter.done.set()

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
        """Return the newest ``limit`` audit lines without scanning older history.

        Audit records are append-only JSONL. Reading from EOF lets bounded API
        requests scale with the requested tail (plus the size of those lines)
        rather than with the total lifetime audit file. The scan preserves the
        previous corruption semantics: overlong selected lines are marked as
        truncated, empty/invalid selected lines are returned for the caller to
        label, and output remains chronological (oldest-to-newest within the
        selected tail).
        """

        if limit <= 0:
            return []

        records_newest_first: list[tuple[bytes, bool]] = []
        current_reversed = bytearray()
        truncated = False
        descriptor = self._open_read_descriptor(self.audit_path, "audit file")

        with os.fdopen(descriptor, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            file_size = handle.tell()
            position = file_size
            at_eof = True

            while position > 0 and len(records_newest_first) < limit:
                read_size = min(8192, position)
                position -= read_size
                handle.seek(position)
                chunk = handle.read(read_size)

                for byte in reversed(chunk):
                    if byte == 0x0A:
                        if at_eof:
                            at_eof = False
                            continue

                        records_newest_first.append(
                            (bytes(reversed(current_reversed)), truncated)
                        )
                        current_reversed.clear()
                        truncated = False
                        if len(records_newest_first) >= limit:
                            break
                    else:
                        at_eof = False
                        if len(current_reversed) < MAX_AUDIT_LINE_BYTES:
                            current_reversed.append(byte)
                        else:
                            truncated = True

            if len(records_newest_first) < limit:
                if current_reversed or truncated:
                    records_newest_first.append(
                        (bytes(reversed(current_reversed)), truncated)
                    )
                elif file_size > 0:
                    handle.seek(0)
                    if handle.read(1) == b"\n":
                        records_newest_first.append((b"", False))

        records_newest_first.reverse()
        return records_newest_first

    def get_registry(self) -> dict[str, Any]:
        with self._lock:
            descriptor = self._open_read_descriptor(
                self.registry_path, "registry file"
            )
            with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
                value = json.load(handle)

            if not isinstance(value, dict):
                raise ValueError("registry must contain a JSON object")

            return validate_json_resource(value)

    def patch_registry(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = self.get_registry()
            current.update(values)
            validate_json_resource(current)
            self._atomic_write_json(self.registry_path, current)
            return current

    def transact_registry(self, operation: RegistryTransaction[T]) -> T:
        """Execute a registry read/derive/write operation under one lock.

        The callback receives the latest validated registry snapshot while the
        store lock is held. It returns a top-level patch (or ``None`` for a
        read/decision-only transaction) plus an arbitrary result. Exceptions
        abort the transaction before any registry write occurs.

        This primitive exists to prevent lost updates when callers need to
        derive a protected namespace map from current registry state. It does
        not make the audit log and registry a single cross-file transaction.
        """
        with self._lock:
            current = self.get_registry()
            patch, result = operation(current)
            if patch is None:
                return result
            if not isinstance(patch, dict):
                raise TypeError("registry transaction patch must be a dict or None")
            updated = dict(current)
            updated.update(patch)
            validate_json_resource(updated)
            self._atomic_write_json(self.registry_path, updated)
            return result

    def check_storage(self) -> tuple[bool, str]:
        probe = self.root / f".readiness-{secrets.token_hex(8)}"
        try:
            self._secure_mode(self.root, 0o700, "data directory")
            self._secure_mode(self.registry_path, 0o600, "registry file")
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
        except (OSError, RuntimeError, json.JSONDecodeError, ValueError) as exc:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
            return False, str(exc)
        return True, "persistent storage is readable, writable, and secured"

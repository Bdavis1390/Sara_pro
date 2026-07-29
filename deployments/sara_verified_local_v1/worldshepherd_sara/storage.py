from __future__ import annotations

import json
import os
import secrets
import stat
import threading
from collections import deque
from pathlib import Path
from typing import Any

from .limits import MAX_AUDIT_LINE_BYTES, validate_json_resource
from .models import AuditRecord


class DurableStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._secure_mode(root, 0o700, "data directory")
        self.root = root
        self.audit_path = root / "audit.jsonl"
        self.registry_path = root / "registry.json"
        self._lock = threading.RLock()
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

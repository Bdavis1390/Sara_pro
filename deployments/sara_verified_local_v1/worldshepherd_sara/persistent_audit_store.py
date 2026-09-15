from __future__ import annotations

import os
import stat
from pathlib import Path

from .storage import DurableStore


class PersistentAuditDescriptorStore(DurableStore):
    """Experimental one-record-per-fsync audit writer with a persistent fd.

    This prototype intentionally preserves the baseline durability contract:
    every ``append_audit`` call remains serialized and returns only after the
    record has been written and ``fsync`` has completed.  The optimization is
    limited to removing repeated open/fchmod/close work from the serialized
    write path.

    The descriptor is bound to the originally opened regular file.  Before and
    after every write we compare the descriptor identity to the path identity
    and require mode 0600.  External path replacement or permission drift is
    therefore a fail-closed condition rather than a silent redirect.
    """

    def __init__(self, data_dir: str | Path | None = None) -> None:
        if os.getenv("SARA_AUDIT_GROUP_COMMIT", "0") == "1":
            raise RuntimeError(
                "Persistent audit descriptor experiment is incompatible with "
                "SARA_AUDIT_GROUP_COMMIT"
            )
        super().__init__(data_dir=data_dir, audit_group_commit=False)
        self._audit_fd: int | None = None
        self._audit_identity: tuple[int, int] | None = None
        self._audit_closed = False

    def _open_persistent_audit_descriptor(self) -> int:
        if self._audit_closed:
            raise RuntimeError("Persistent audit descriptor store is closed")
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_APPEND
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(self.audit_path, flags, 0o600)
        try:
            self._secure_descriptor(descriptor, 0o600, "audit file")
            descriptor_status = os.fstat(descriptor)
            if not stat.S_ISREG(descriptor_status.st_mode):
                raise RuntimeError("Persistent audit descriptor is not a regular file")
            path_status = os.lstat(self.audit_path)
            if not stat.S_ISREG(path_status.st_mode):
                raise RuntimeError("Persistent audit path is not a regular file")
            identity = (descriptor_status.st_dev, descriptor_status.st_ino)
            if identity != (path_status.st_dev, path_status.st_ino):
                raise RuntimeError("Persistent audit descriptor/path identity mismatch")
            if stat.S_IMODE(path_status.st_mode) != 0o600:
                raise RuntimeError("Persistent audit path mode changed from 0600")
        except Exception:
            os.close(descriptor)
            raise
        self._audit_fd = descriptor
        self._audit_identity = identity
        return descriptor

    def _verify_persistent_audit_descriptor(self) -> int:
        if self._audit_closed:
            raise RuntimeError("Persistent audit descriptor store is closed")
        descriptor = self._audit_fd
        if descriptor is None:
            return self._open_persistent_audit_descriptor()

        try:
            descriptor_status = os.fstat(descriptor)
            path_status = os.lstat(self.audit_path)
        except OSError as exc:
            raise RuntimeError(
                f"Unable to verify persistent audit descriptor: {exc}"
            ) from exc

        if not stat.S_ISREG(descriptor_status.st_mode):
            raise RuntimeError("Persistent audit descriptor is not a regular file")
        if not stat.S_ISREG(path_status.st_mode):
            raise RuntimeError("Persistent audit path is not a regular file")
        identity = (descriptor_status.st_dev, descriptor_status.st_ino)
        if identity != self._audit_identity:
            raise RuntimeError("Persistent audit descriptor identity changed")
        if identity != (path_status.st_dev, path_status.st_ino):
            raise RuntimeError("Persistent audit path was replaced")
        if stat.S_IMODE(descriptor_status.st_mode) != 0o600:
            raise RuntimeError("Persistent audit descriptor mode changed from 0600")
        if stat.S_IMODE(path_status.st_mode) != 0o600:
            raise RuntimeError("Persistent audit path mode changed from 0600")
        return descriptor

    @staticmethod
    def _write_all(descriptor: int, payload: bytes) -> None:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("audit write made no forward progress")
            remaining = remaining[written:]

    def _write_audit_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        payload = "".join(f"{line}\n" for line in lines).encode("utf-8")
        with self._lock:
            descriptor = self._verify_persistent_audit_descriptor()
            self._write_all(descriptor, payload)
            os.fsync(descriptor)
            # Detect external replacement or permission drift that occurred
            # during the write.  The caller receives failure rather than a
            # success acknowledgment against an ambiguous path identity.
            self._verify_persistent_audit_descriptor()

    def close(self) -> None:
        with self._lock:
            if self._audit_fd is not None:
                os.close(self._audit_fd)
                self._audit_fd = None
            self._audit_closed = True

    def __del__(self) -> None:
        descriptor = getattr(self, "_audit_fd", None)
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
            self._audit_fd = None

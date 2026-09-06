from __future__ import annotations

import json
import os
import stat
import threading
from collections import deque
from pathlib import Path

from .limits import MAX_AUDIT_LINE_BYTES
from .physics_validation import PhysicsVerificationRecord


class PhysicsEvidenceStore:
    """Append-only local store for bounded PVK verification records."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = root
        self.path = root / "physics_records.jsonl"
        self._lock = threading.RLock()
        self._secure_mode(root, 0o700, expect_directory=True)
        if self.path.exists():
            self._secure_mode(self.path, 0o600, expect_directory=False)

    @staticmethod
    def _secure_mode(path: Path, mode: int, *, expect_directory: bool) -> None:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        if expect_directory:
            flags |= getattr(os, "O_DIRECTORY", 0)
        descriptor = os.open(path, flags)
        try:
            file_status = os.fstat(descriptor)
            if expect_directory and not stat.S_ISDIR(file_status.st_mode):
                raise RuntimeError("physics store root is not a directory")
            if not expect_directory and not stat.S_ISREG(file_status.st_mode):
                raise RuntimeError("physics store path is not a regular file")
            os.fchmod(descriptor, mode)
            if stat.S_IMODE(os.fstat(descriptor).st_mode) != mode:
                raise RuntimeError("unable to enforce physics-store permissions")
        finally:
            os.close(descriptor)

    def append(self, record: PhysicsVerificationRecord) -> None:
        line = record.model_dump_json(exclude_none=True)
        if len(line.encode("utf-8")) > MAX_AUDIT_LINE_BYTES:
            raise ValueError("physics verification record exceeds maximum line size")
        with self._lock:
            descriptor = os.open(
                self.path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_APPEND
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    raise RuntimeError("physics store path is not a regular file")
                os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                    handle.write(line + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            self._secure_mode(self.path, 0o600, expect_directory=False)

    def read_recent(
        self,
        *,
        limit: int,
        project_id: str | None = None,
        artifact_id: str | None = None,
    ) -> list[PhysicsVerificationRecord]:
        with self._lock:
            if not self.path.exists():
                return []
            self._secure_mode(self.path, 0o600, expect_directory=False)
            lines: deque[str] = deque(maxlen=max(limit * 4, limit))
            with self.path.open("r", encoding="utf-8") as handle:
                for raw in handle:
                    lines.append(raw)

        records: list[PhysicsVerificationRecord] = []
        for raw in reversed(lines):
            try:
                record = PhysicsVerificationRecord.model_validate_json(raw)
            except (ValueError, json.JSONDecodeError):
                continue
            if project_id is not None and record.project_id != project_id:
                continue
            if artifact_id is not None and record.artifact_id != artifact_id:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        records.reverse()
        return records

    def status(self) -> dict[str, int]:
        with self._lock:
            if not self.path.exists():
                return {"records": 0}
            count = 0
            with self.path.open("r", encoding="utf-8") as handle:
                for _ in handle:
                    count += 1
            return {"records": count}

    def check_storage(self) -> tuple[bool, str]:
        try:
            self._secure_mode(self.root, 0o700, expect_directory=True)
            if self.path.exists():
                self._secure_mode(self.path, 0o600, expect_directory=False)
                self.read_recent(limit=1)
        except (OSError, RuntimeError, ValueError) as exc:
            return False, str(exc)
        return True, "physics evidence storage is readable and secured"

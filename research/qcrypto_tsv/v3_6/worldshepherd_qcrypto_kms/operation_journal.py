"""Durable, fail-closed signing operation journal.

The journal exists to prevent an ambiguous KMS Sign outcome from being retried after
process restart or across concurrent workers. A signing operation is atomically
claimed *before* the remote Sign call. If the process dies after the claim, the
record remains IN_FLIGHT and is treated as ambiguous on the next startup.

This intentionally favors availability loss over duplicate signing after an
uncertain remote outcome.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

try:  # Linux/Unix production target.
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - non-POSIX platforms are not production targets here.
    fcntl = None


class OperationJournalError(RuntimeError):
    pass


class OperationJournalConflict(OperationJournalError):
    pass


@dataclass(frozen=True)
class JournalRecord:
    operation_id: str
    state: str
    binding: dict[str, str]
    result: dict[str, Any] | None
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "state": self.state,
            "binding": dict(self.binding),
            "result": self.result,
            "updated_at": self.updated_at,
        }


class FileOperationJournal:
    """One JSON record per operation, guarded by an advisory process lock."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = pathlib.Path(root)
        if self.root.exists() and self.root.is_symlink():
            raise OperationJournalError("journal root must not be a symbolic link")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.root.is_dir():
            raise OperationJournalError("journal root is not a directory")
        # The journal is security-state, not a shared cache. Tighten permissions even
        # when the directory pre-existed under a permissive umask.
        os.chmod(self.root, 0o700)
        self._lock_path = self.root / ".journal.lock"
        if self._lock_path.exists() and self._lock_path.is_symlink():
            raise OperationJournalError("journal lock must not be a symbolic link")
        self._lock_path.touch(exist_ok=True, mode=0o600)
        os.chmod(self._lock_path, 0o600)

    @staticmethod
    def _safe_name(operation_id: str) -> str:
        if not operation_id or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for c in operation_id):
            raise OperationJournalError("operation_id contains unsupported characters")
        return operation_id + ".json"

    def _path(self, operation_id: str) -> pathlib.Path:
        return self.root / self._safe_name(operation_id)

    @contextmanager
    def _locked(self) -> Iterator[None]:
        if fcntl is None:
            raise OperationJournalError("POSIX file locking is required for production journal use")
        with self._lock_path.open("r+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _read_unlocked(self, operation_id: str) -> JournalRecord | None:
        path = self._path(operation_id)
        if not path.exists():
            return None
        if path.is_symlink():
            raise OperationJournalError("journal record must not be a symbolic link")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise OperationJournalError(f"journal record is unreadable: {path.name}") from exc
        if not isinstance(raw, dict):
            raise OperationJournalError("journal record must be a JSON object")
        binding = raw.get("binding")
        if not isinstance(binding, dict):
            raise OperationJournalError("journal record has invalid binding")
        result = raw.get("result")
        if result is not None and not isinstance(result, dict):
            raise OperationJournalError("journal record has invalid result")
        return JournalRecord(
            operation_id=str(raw.get("operation_id", "")),
            state=str(raw.get("state", "")),
            binding={str(k): str(v) for k, v in binding.items()},
            result=result,
            updated_at=str(raw.get("updated_at", "")),
        )

    def _write_unlocked(self, record: JournalRecord) -> None:
        path = self._path(record.operation_id)
        payload = json.dumps(record.to_dict(), sort_keys=True, indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=".journal-", suffix=".tmp", dir=str(self.root))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            dir_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _assert_binding(record: JournalRecord, binding: dict[str, str]) -> None:
        if record.binding != binding:
            raise OperationJournalConflict("operation_id is already bound to different signing inputs")

    def get(self, operation_id: str) -> JournalRecord | None:
        with self._locked():
            return self._read_unlocked(operation_id)

    def claim_for_sign(self, operation_id: str, binding: dict[str, str]) -> tuple[JournalRecord, bool]:
        """Atomically claim a signing operation before any remote Sign request.

        New claims are written as IN_FLIGHT. Existing SIGNED records are returned so
        callers can replay the recorded result without a second KMS call. Existing
        IN_FLIGHT or INDETERMINATE records are returned and must not be retried.
        """
        with self._locked():
            prior = self._read_unlocked(operation_id)
            if prior is not None:
                self._assert_binding(prior, binding)
                return prior, False
            record = JournalRecord(
                operation_id=operation_id,
                state="IN_FLIGHT",
                binding=dict(binding),
                result=None,
                updated_at=self._now(),
            )
            self._write_unlocked(record)
            return record, True

    def mark_signed(self, operation_id: str, binding: dict[str, str], result: dict[str, Any]) -> JournalRecord:
        with self._locked():
            prior = self._read_unlocked(operation_id)
            if prior is None:
                raise OperationJournalConflict("cannot complete an unclaimed signing operation")
            self._assert_binding(prior, binding)
            if prior.state == "SIGNED":
                if prior.result != result:
                    raise OperationJournalConflict("signed result conflicts with durable journal")
                return prior
            if prior.state != "IN_FLIGHT":
                raise OperationJournalConflict(f"cannot mark {prior.state} operation as SIGNED")
            record = JournalRecord(
                operation_id=operation_id,
                state="SIGNED",
                binding=dict(binding),
                result=dict(result),
                updated_at=self._now(),
            )
            self._write_unlocked(record)
            return record

    def mark_indeterminate(self, operation_id: str, binding: dict[str, str]) -> JournalRecord:
        with self._locked():
            prior = self._read_unlocked(operation_id)
            if prior is None:
                raise OperationJournalConflict("cannot mark an unclaimed signing operation")
            self._assert_binding(prior, binding)
            if prior.state == "SIGNED":
                return prior
            record = JournalRecord(
                operation_id=operation_id,
                state="INDETERMINATE",
                binding=dict(binding),
                result=None,
                updated_at=self._now(),
            )
            self._write_unlocked(record)
            return record

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .models import AuditRecord


class DurableStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root = root
        self.audit_path = root / "audit.jsonl"
        self.registry_path = root / "registry.json"
        self._lock = threading.RLock()
        if not self.registry_path.exists():
            self._atomic_write_json(self.registry_path, {})

    def _atomic_write_json(self, path: Path, value: Any) -> None:
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    def append_audit(self, record: AuditRecord) -> None:
        line = record.model_dump_json(exclude_none=True)
        with self._lock:
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def read_audit(self, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            if not self.audit_path.exists():
                return []
            lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records.append({"event": "audit_corruption_detected", "raw": line})
        return records

    def get_registry(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))

    def patch_registry(self, values: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = self.get_registry()
            current.update(values)
            self._atomic_write_json(self.registry_path, current)
            return current

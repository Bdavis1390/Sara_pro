from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .hmaa import AssuranceAssessment, HMAAEvent, verify_event_seal
from .storage import DurableStore


MAX_HMAA_LINE_BYTES = 262_144


class HMAAPersistedRecord(BaseModel):
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event: HMAAEvent
    assessment: AssuranceAssessment
    state: dict[str, Any] | None = None


class HMAAEvidenceStore:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        root = Path(data_dir or os.getenv("SARA_DATA_DIR", "./data")).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        DurableStore._secure_mode(root, 0o700, "HMAA data directory")
        self.root = root
        self.path = root / "hmaa_evidence.jsonl"
        self._lock = threading.RLock()
        if self.path.exists():
            DurableStore._secure_mode(self.path, 0o600, "HMAA evidence file")

    def append(
        self,
        event: HMAAEvent,
        assessment: AssuranceAssessment,
        *,
        state: dict[str, Any] | None = None,
    ) -> HMAAPersistedRecord:
        if not verify_event_seal(event):
            raise ValueError("HMAA event must carry a valid cryptographic seal")

        with self._lock:
            prior = self.read_recent(limit=1, mission_id=event.mission_id)
            expected_previous = prior[-1].event.event_hash if prior else None
            if event.previous_event_hash != expected_previous:
                raise ValueError(
                    "HMAA event does not continue the persisted mission evidence chain"
                )

            record = HMAAPersistedRecord(
                event=event,
                assessment=assessment,
                state=state,
            )
            encoded = record.model_dump_json(exclude_none=True).encode("utf-8")
            if len(encoded) > MAX_HMAA_LINE_BYTES:
                raise ValueError("HMAA evidence record exceeds the maximum line size")

            descriptor = os.open(
                self.path,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_APPEND
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                DurableStore._secure_descriptor(
                    descriptor, 0o600, "HMAA evidence file"
                )
                with os.fdopen(descriptor, "ab") as handle:
                    handle.write(encoded + b"\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise

            DurableStore._secure_mode(
                self.path, 0o600, "HMAA evidence file"
            )
            return record

    def read_recent(
        self,
        limit: int,
        mission_id: str | None = None,
    ) -> list[HMAAPersistedRecord]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        with self._lock:
            try:
                self.path.lstat()
            except FileNotFoundError:
                return []

            descriptor = DurableStore._open_read_descriptor(
                self.path, "HMAA evidence file"
            )
            matches: list[HMAAPersistedRecord] = []
            with os.fdopen(descriptor, "rb") as handle:
                while True:
                    raw = handle.readline(MAX_HMAA_LINE_BYTES + 1)
                    if not raw:
                        break
                    if len(raw) > MAX_HMAA_LINE_BYTES:
                        if not raw.endswith(b"\n"):
                            while raw and not raw.endswith(b"\n"):
                                raw = handle.readline(MAX_HMAA_LINE_BYTES + 1)
                        raise RuntimeError(
                            "HMAA evidence corruption detected: line too long"
                        )
                    try:
                        record = HMAAPersistedRecord.model_validate_json(raw)
                    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                        raise RuntimeError(
                            "HMAA evidence corruption detected: invalid record"
                        ) from exc
                    if mission_id is None or record.event.mission_id == mission_id:
                        matches.append(record)
                        if len(matches) > limit:
                            del matches[0]
            return matches

    def status(self) -> dict[str, Any]:
        latest = self.read_recent(limit=1)
        return {
            "configured": True,
            "append_only_file": self.path.name,
            "records_available": bool(latest),
            "latest_event_hash": (
                latest[-1].event.event_hash if latest else None
            ),
            "latest_mission_id": (
                latest[-1].event.mission_id if latest else None
            ),
        }

    def check_storage(self) -> tuple[bool, str]:
        try:
            DurableStore._secure_mode(
                self.root, 0o700, "HMAA data directory"
            )
            if self.path.exists():
                DurableStore._secure_mode(
                    self.path, 0o600, "HMAA evidence file"
                )
                self.read_recent(limit=1)
        except (OSError, RuntimeError, ValueError) as exc:
            return False, str(exc)
        return True, "HMAA evidence storage is readable and secured"

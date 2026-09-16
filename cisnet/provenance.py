from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AuditEvent:
    seq: int
    t_s: int
    event: str
    detail: Dict[str, Any]
    prev_hash: str
    hash: str


class EchoLedger:
    """Hash-chained local evidence ledger for simulation events.

    Provides tamper evidence inside the generated record. It is not a substitute
    for signatures, external timestamping, secure hardware, or BPSec.
    """

    def __init__(self) -> None:
        self.events: List[AuditEvent] = []

    @staticmethod
    def _digest(seq: int, t_s: int, event: str, detail: Dict[str, Any], prev_hash: str) -> str:
        payload = json.dumps(
            {"seq": seq, "t_s": t_s, "event": event, "detail": detail, "prev_hash": prev_hash},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def append(self, t_s: int, event: str, **detail: Any) -> AuditEvent:
        seq = len(self.events)
        prev_hash = self.events[-1].hash if self.events else "GENESIS"
        digest = self._digest(seq, t_s, event, detail, prev_hash)
        record = AuditEvent(seq, t_s, event, detail, prev_hash, digest)
        self.events.append(record)
        return record

    def verify(self) -> bool:
        previous = "GENESIS"
        for index, record in enumerate(self.events):
            if record.seq != index or record.prev_hash != previous:
                return False
            expected = self._digest(record.seq, record.t_s, record.event, record.detail, record.prev_hash)
            if expected != record.hash:
                return False
            previous = record.hash
        return True

    def as_dicts(self) -> List[Dict[str, Any]]:
        return [asdict(event) for event in self.events]

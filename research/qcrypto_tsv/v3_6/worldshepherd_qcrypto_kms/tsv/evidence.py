from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EvidenceEvent:
    sequence: int
    event_type: str
    occurred_at: str
    payload_sha256: str
    previous_hash: str
    event_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceChain:
    """Append-only SHA-256 evidence receipts for local provenance.

    This is a tamper-evident hash chain, not a digital signature, timestamping
    authority, blockchain anchoring scheme, or independent attestation.
    """

    GENESIS = "0" * 64

    def __init__(self, events: Optional[Iterable[EvidenceEvent]] = None):
        self._events: List[EvidenceEvent] = list(events or [])
        if self._events and not self.verify():
            raise ValueError("invalid evidence chain")

    @property
    def events(self) -> List[EvidenceEvent]:
        return list(self._events)

    def append(self, event_type: str, payload: Any, *, occurred_at: datetime) -> EvidenceEvent:
        if not event_type or not event_type.strip():
            raise ValueError("event_type is required")
        payload_digest = sha256_hex(canonical_json(payload))
        previous = self._events[-1].event_hash if self._events else self.GENESIS
        base = {
            "sequence": len(self._events) + 1,
            "event_type": event_type.strip(),
            "occurred_at": _iso_utc(occurred_at),
            "payload_sha256": payload_digest,
            "previous_hash": previous,
        }
        event_hash = sha256_hex(canonical_json(base))
        event = EvidenceEvent(event_hash=event_hash, **base)
        self._events.append(event)
        return event

    def verify(self) -> bool:
        previous = self.GENESIS
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.sequence != expected_sequence or event.previous_hash != previous:
                return False
            base = {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "payload_sha256": event.payload_sha256,
                "previous_hash": event.previous_hash,
            }
            if sha256_hex(canonical_json(base)) != event.event_hash:
                return False
            previous = event.event_hash
        return True

    def head(self) -> str:
        return self._events[-1].event_hash if self._events else self.GENESIS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": "SHA-256",
            "attestation_type": "LOCAL_TAMPER_EVIDENT_HASH_CHAIN_ONLY",
            "head": self.head(),
            "verified": self.verify(),
            "events": [event.to_dict() for event in self._events],
        }

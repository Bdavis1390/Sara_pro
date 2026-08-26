from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Envelope:
    sequence: int
    source: str
    payload: dict[str, Any]
    timestamp_ms: int


@dataclass(frozen=True)
class FaultProfile:
    """Deterministic transport-fault profile for software qualification only."""

    drop_sequences: frozenset[int] = frozenset()
    duplicate_sequences: frozenset[int] = frozenset()
    stale_sequences: frozenset[int] = frozenset()
    added_latency_ms: int = 0
    reorder_windows: tuple[tuple[int, int], ...] = ()


@dataclass
class FaultResult:
    delivered: list[Envelope] = field(default_factory=list)
    dropped: list[int] = field(default_factory=list)
    duplicated: list[int] = field(default_factory=list)
    stale: list[int] = field(default_factory=list)

    def replay_signature(self) -> tuple[tuple[int, str, int], ...]:
        return tuple((m.sequence, m.source, m.timestamp_ms) for m in self.delivered)


def apply_fault_profile(messages: list[Envelope], profile: FaultProfile) -> FaultResult:
    """Apply deterministic DDIL-like transport faults.

    This models message delivery behavior only. It does not establish RF/link,
    tactical-network, or operational DDIL performance.
    """
    result = FaultResult()
    working: list[Envelope] = []

    for message in messages:
        if message.sequence in profile.drop_sequences:
            result.dropped.append(message.sequence)
            continue

        timestamp = message.timestamp_ms + profile.added_latency_ms
        payload = dict(message.payload)
        if message.sequence in profile.stale_sequences:
            payload["_ws_stale"] = True
            result.stale.append(message.sequence)

        delivered = Envelope(
            sequence=message.sequence,
            source=message.source,
            payload=payload,
            timestamp_ms=timestamp,
        )
        working.append(delivered)

        if message.sequence in profile.duplicate_sequences:
            working.append(delivered)
            result.duplicated.append(message.sequence)

    for start, end in profile.reorder_windows:
        indexes = [i for i, item in enumerate(working) if start <= item.sequence <= end]
        if indexes:
            values = [working[i] for i in indexes][::-1]
            for index, value in zip(indexes, values):
                working[index] = value

    result.delivered = working
    return result

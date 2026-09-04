from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from .hmaa import HMAAEvent


def _first(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _timestamp(payload: Mapping[str, Any]) -> datetime:
    value = _first(
        payload,
        "source_timestamp",
        "timestamp",
        "last_updated_at",
        "lastUpdatedAt",
        "update_time",
        "updateTime",
    )
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError("unsupported source timestamp type")


def normalize_entity_event(
    payload: Mapping[str, Any], *, mission_id: str
) -> HMAAEvent:
    entity_id = _first(payload, "entity_id", "entityId", "id")
    if not entity_id:
        raise ValueError("entity update is missing an entity identifier")

    stream_event_type = _first(payload, "event_type", "eventType", "type")
    return HMAAEvent(
        event_id=str(uuid4()),
        mission_id=mission_id,
        entity_id=str(entity_id),
        event_type=f"ENTITY_{str(stream_event_type or 'UPDATE').upper()}",
        source_timestamp=_timestamp(payload),
        payload=dict(payload),
    )


def normalize_task_event(
    payload: Mapping[str, Any], *, mission_id: str
) -> HMAAEvent:
    task_id = _first(payload, "task_id", "taskId", "id")
    if not task_id:
        raise ValueError("task update is missing a task identifier")

    status = _first(payload, "status", "task_status", "taskStatus")
    return HMAAEvent(
        event_id=str(uuid4()),
        mission_id=mission_id,
        task_id=str(task_id),
        entity_id=(
            str(_first(payload, "entity_id", "entityId", "agent_id", "agentId"))
            if _first(payload, "entity_id", "entityId", "agent_id", "agentId")
            is not None
            else None
        ),
        event_type=f"TASK_{str(status or 'UPDATE').upper()}",
        source_timestamp=_timestamp(payload),
        payload=dict(payload),
    )


def heartbeat_event(*, mission_id: str, stream: str) -> HMAAEvent:
    now = datetime.now(timezone.utc)
    return HMAAEvent(
        event_id=str(uuid4()),
        mission_id=mission_id,
        event_type="HEARTBEAT",
        source_timestamp=now,
        payload={"stream": stream},
    )


def reconnect_event(
    *, mission_id: str, stream: str, attempt: int
) -> HMAAEvent:
    if attempt < 1:
        raise ValueError("reconnect attempt must be at least 1")
    now = datetime.now(timezone.utc)
    return HMAAEvent(
        event_id=str(uuid4()),
        mission_id=mission_id,
        event_type="STREAM_RECONNECT",
        source_timestamp=now,
        payload={"stream": stream, "attempt": attempt},
    )

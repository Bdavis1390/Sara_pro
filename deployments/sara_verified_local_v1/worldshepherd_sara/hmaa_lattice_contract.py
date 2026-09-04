from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel

from .hmaa import HMAAEvent
from .hmaa_adapter import normalize_entity_event, normalize_task_event


LATTICE_PUBLIC_CONTRACT_VERSION = "lattice-public-rest-contract-2026-09-04"


class LatticeStream(StrEnum):
    ENTITIES = "entities"
    TASKS = "tasks"


class LatticeEnvelopeKind(StrEnum):
    HEARTBEAT = "heartbeat"
    ENTITY = "entity"
    TASK = "task"


class LatticeContractEvent(BaseModel):
    contract_version: str = LATTICE_PUBLIC_CONTRACT_VERSION
    stream: LatticeStream
    kind: LatticeEnvelopeKind
    source_event_id: str
    hmaa_event: HMAAEvent


@runtime_checkable
class LatticeReadTransport(Protocol):
    """Credentials-agnostic, read-only transport boundary for future adapters."""

    def stream_entities(
        self, request: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]: ...

    def stream_tasks(
        self, request: Mapping[str, Any]
    ) -> Iterable[Mapping[str, Any]]: ...


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_event_id(stream: LatticeStream, message: Mapping[str, Any]) -> str:
    return f"lattice:{stream.value}:sha256:{_canonical_sha256(message)}"


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    raise ValueError("stream heartbeat is missing a usable timestamp")


def _heartbeat_timestamp(payload: Mapping[str, Any]) -> datetime:
    for key in ("timestamp", "time", "sourceTimestamp", "source_timestamp"):
        if key in payload:
            return _parse_timestamp(payload[key])
    raise ValueError("stream heartbeat is missing a timestamp")


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def validate_entity_stream_request(request: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(request)

    if "heartbeatIntervalMS" in result:
        value = result["heartbeatIntervalMS"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("heartbeatIntervalMS must be a positive integer")

    if "preExistingOnly" in result and not isinstance(result["preExistingOnly"], bool):
        raise ValueError("preExistingOnly must be boolean")

    if "componentsToInclude" in result:
        components = result["componentsToInclude"]
        if not isinstance(components, list) or any(
            not isinstance(item, str) or not item.strip() for item in components
        ):
            raise ValueError("componentsToInclude must be a list of non-empty strings")

    if "filter" in result:
        _require_mapping(result["filter"], "filter")

    return result


def validate_task_stream_request(request: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(request)

    if "heartbeatIntervalMs" in result:
        value = result["heartbeatIntervalMs"]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("heartbeatIntervalMs must be a positive integer")

    if "rateLimit" in result:
        rate_limit = result["rateLimit"]
        if isinstance(rate_limit, bool) or not isinstance(rate_limit, int):
            raise ValueError("rateLimit must be an integer")
        if rate_limit < 0 or (rate_limit != 0 and rate_limit < 250):
            raise ValueError("rateLimit must be 0 or at least 250 milliseconds")

    if "excludePreexistingTasks" in result and not isinstance(
        result["excludePreexistingTasks"], bool
    ):
        raise ValueError("excludePreexistingTasks must be boolean")

    parent_task_id = result.get("parentTaskId")
    if parent_task_id is not None:
        if not isinstance(parent_task_id, str) or not parent_task_id.strip():
            raise ValueError("parentTaskId must be a non-empty string")
        mutually_exclusive = {
            "updateStartTime",
            "assignee",
            "statusFilter",
            "taskType",
        }
        conflict = sorted(mutually_exclusive.intersection(result))
        if conflict:
            raise ValueError(
                "parentTaskId is mutually exclusive with: " + ", ".join(conflict)
            )

    for field in ("assignee", "statusFilter", "taskType"):
        if field in result:
            _require_mapping(result[field], field)

    if "updateStartTime" in result and (
        not isinstance(result["updateStartTime"], str)
        or not result["updateStartTime"].strip()
    ):
        raise ValueError("updateStartTime must be a non-empty timestamp string")

    return result


def parse_entity_stream_message(
    message: Mapping[str, Any], *, mission_id: str
) -> LatticeContractEvent:
    heartbeat = message.get("heartbeat")
    entity_wrapper = message.get("entity")
    present = int(heartbeat is not None) + int(entity_wrapper is not None)
    if present != 1:
        raise ValueError("entity stream message must contain exactly one heartbeat or entity")

    source_event_id = _source_event_id(LatticeStream.ENTITIES, message)
    if heartbeat is not None:
        heartbeat_payload = _require_mapping(heartbeat, "heartbeat")
        event = HMAAEvent(
            event_id=source_event_id,
            mission_id=mission_id,
            source_system="lattice-public-contract",
            event_type="HEARTBEAT",
            source_timestamp=_heartbeat_timestamp(heartbeat_payload),
            payload={"stream": LatticeStream.ENTITIES.value, **dict(heartbeat_payload)},
        )
        return LatticeContractEvent(
            stream=LatticeStream.ENTITIES,
            kind=LatticeEnvelopeKind.HEARTBEAT,
            source_event_id=source_event_id,
            hmaa_event=event,
        )

    wrapper = _require_mapping(entity_wrapper, "entity")
    entity_payload = _require_mapping(wrapper.get("entity", wrapper), "entity payload")
    normalized_payload = dict(entity_payload)
    stream_event_type = wrapper.get("eventType", wrapper.get("event_type"))
    if stream_event_type is not None:
        normalized_payload.setdefault("eventType", stream_event_type)
    event = normalize_entity_event(normalized_payload, mission_id=mission_id).model_copy(
        update={
            "event_id": source_event_id,
            "source_system": "lattice-public-contract",
        }
    )
    return LatticeContractEvent(
        stream=LatticeStream.ENTITIES,
        kind=LatticeEnvelopeKind.ENTITY,
        source_event_id=source_event_id,
        hmaa_event=event,
    )


def parse_task_stream_message(
    message: Mapping[str, Any], *, mission_id: str
) -> LatticeContractEvent:
    heartbeat = message.get("heartbeat")
    task_wrapper = message.get("task_event", message.get("taskEvent"))
    present = int(heartbeat is not None) + int(task_wrapper is not None)
    if present != 1:
        raise ValueError("task stream message must contain exactly one heartbeat or task_event")

    source_event_id = _source_event_id(LatticeStream.TASKS, message)
    if heartbeat is not None:
        heartbeat_payload = _require_mapping(heartbeat, "heartbeat")
        event = HMAAEvent(
            event_id=source_event_id,
            mission_id=mission_id,
            source_system="lattice-public-contract",
            event_type="HEARTBEAT",
            source_timestamp=_heartbeat_timestamp(heartbeat_payload),
            payload={"stream": LatticeStream.TASKS.value, **dict(heartbeat_payload)},
        )
        return LatticeContractEvent(
            stream=LatticeStream.TASKS,
            kind=LatticeEnvelopeKind.HEARTBEAT,
            source_event_id=source_event_id,
            hmaa_event=event,
        )

    wrapper = _require_mapping(task_wrapper, "task_event")
    task_payload = _require_mapping(wrapper.get("task", wrapper), "task payload")
    normalized_payload = dict(task_payload)
    event_type = wrapper.get("eventType", wrapper.get("event_type"))
    if event_type is not None and "status" not in normalized_payload:
        normalized_payload["status"] = str(event_type)
    event = normalize_task_event(normalized_payload, mission_id=mission_id).model_copy(
        update={
            "event_id": source_event_id,
            "source_system": "lattice-public-contract",
        }
    )
    return LatticeContractEvent(
        stream=LatticeStream.TASKS,
        kind=LatticeEnvelopeKind.TASK,
        source_event_id=source_event_id,
        hmaa_event=event,
    )

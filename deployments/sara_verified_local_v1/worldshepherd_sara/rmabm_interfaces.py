from __future__ import annotations

import base64
import hashlib
from typing import Any, Literal

from pydantic import BaseModel, Field

from .rmabm import ProvenancedObservation


class InterfaceConformanceError(ValueError):
    """Raised when a synthetic external record cannot be safely normalized."""


class NormalizedInterfaceRecord(BaseModel):
    schema_family: Literal["synthetic_alpha", "synthetic_beta"]
    schema_version: str = Field(min_length=1)
    observation: ProvenancedObservation


def _verify_payload(payload_b64: str, claimed_sha256: str) -> str:
    try:
        payload = base64.b64decode(payload_b64.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001 - normalize decoder errors
        raise InterfaceConformanceError("payload is not valid base64") from exc

    actual = hashlib.sha256(payload).hexdigest()
    if actual != str(claimed_sha256).lower():
        raise InterfaceConformanceError("payload digest mismatch")
    return actual


def _alpha(record: dict[str, Any]) -> NormalizedInterfaceRecord:
    version = str(record.get("schema_version", ""))
    if version != "1.0":
        raise InterfaceConformanceError(f"unsupported synthetic_alpha schema_version={version!r}")
    try:
        payload_sha256 = _verify_payload(str(record["payload_b64"]), str(record["sha256"]))
        position = record["position"]
        observation = ProvenancedObservation(
            observation_id=str(record["id"]),
            sensor_id=str(record["sensor"]),
            t_seconds=float(record["t_seconds"]),
            x=float(position["x"]),
            y=float(position["y"]),
            confidence=float(record["confidence"]),
            source_sha256=payload_sha256,
            source_status="synthetic",
        )
    except InterfaceConformanceError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert heterogeneous schema failures
        raise InterfaceConformanceError(f"invalid synthetic_alpha record: {exc}") from exc
    return NormalizedInterfaceRecord(schema_family="synthetic_alpha", schema_version=version, observation=observation)


def _beta(record: dict[str, Any]) -> NormalizedInterfaceRecord:
    version = str(record.get("version", ""))
    if version != "2026.1":
        raise InterfaceConformanceError(f"unsupported synthetic_beta schema_version={version!r}")
    try:
        event = record["event"]
        coords = record["coords"]
        quality = record["quality"]
        blob = record["blob"]
        payload_sha256 = _verify_payload(str(blob["b64"]), str(blob["digest_sha256"]))
        observation = ProvenancedObservation(
            observation_id=str(event["key"]),
            sensor_id=str(event["source"]),
            t_seconds=float(event["seconds"]),
            x=float(coords[0]),
            y=float(coords[1]),
            confidence=float(quality["score"]),
            source_sha256=payload_sha256,
            source_status="synthetic",
        )
    except InterfaceConformanceError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert heterogeneous schema failures
        raise InterfaceConformanceError(f"invalid synthetic_beta record: {exc}") from exc
    return NormalizedInterfaceRecord(schema_family="synthetic_beta", schema_version=version, observation=observation)


def normalize_interface_record(
    record: dict[str, Any], *, family: Literal["synthetic_alpha", "synthetic_beta"]
) -> NormalizedInterfaceRecord:
    """Normalize one vendor-neutral synthetic interface record.

    The two schemas are deliberately fictional. They demonstrate interface-adapter
    behavior only and do not model or disclose any BAE, SDA, SSC, Rocket Lab, or
    other vendor proprietary interface.
    """
    if family == "synthetic_alpha":
        return _alpha(record)
    if family == "synthetic_beta":
        return _beta(record)
    raise InterfaceConformanceError(f"unsupported interface family={family!r}")


def normalize_interface_batch(records: list[tuple[str, dict[str, Any]]]) -> list[ProvenancedObservation]:
    normalized = [
        normalize_interface_record(record, family=family).observation
        for family, record in records
    ]
    observation_ids = [item.observation_id for item in normalized]
    if len(set(observation_ids)) != len(observation_ids):
        raise InterfaceConformanceError("normalized observation identifiers must be globally unique")
    return sorted(normalized, key=lambda item: (item.t_seconds, item.observation_id))

"""Read-only Amazon Braket QPU discovery for Worldshepherd QRF.

This module performs no task creation and accepts no AWS credential material.  It is
used immediately before a governed on-demand run so the operator can select an actual
ONLINE physical QPU ARN and retain the device/queue snapshot that informed selection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol


class BraketReadClient(Protocol):
    def search_devices(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def get_device(self, **kwargs: Any) -> Mapping[str, Any]: ...


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


@dataclass(frozen=True)
class BraketQPUCandidate:
    region: str
    device_arn: str
    device_name: str
    provider_name: str
    device_status: str
    device_type: str
    queue_info: tuple[Mapping[str, str], ...]
    device_capabilities_digest: str
    device_snapshot_digest: str


def discover_online_qpus(client: BraketReadClient, *, region: str) -> tuple[BraketQPUCandidate, ...]:
    """Return ONLINE physical QPUs visible to the supplied regional Braket client.

    Amazon Braket's SearchDevices API accepts an empty filters array.  We intentionally
    filter `deviceType == QPU` and `deviceStatus == ONLINE` locally, then call GetDevice
    for each surviving ARN so selection retains queue and capability identity.
    """

    if not region.strip():
        raise ValueError("region is required")

    summaries: list[Mapping[str, Any]] = []
    next_token: str | None = None
    while True:
        request: dict[str, Any] = {"filters": [], "maxResults": 100}
        if next_token:
            request["nextToken"] = next_token
        response = client.search_devices(**request)
        devices = response.get("devices", [])
        if not isinstance(devices, list):
            raise ValueError("Braket search_devices response.devices must be a list")
        summaries.extend(item for item in devices if isinstance(item, Mapping))
        token_value = response.get("nextToken")
        next_token = str(token_value) if token_value else None
        if not next_token:
            break

    candidates: list[BraketQPUCandidate] = []
    for summary in summaries:
        if str(summary.get("deviceType")) != "QPU" or str(summary.get("deviceStatus")) != "ONLINE":
            continue
        arn = str(summary.get("deviceArn", ""))
        if not arn:
            continue
        detail = dict(client.get_device(deviceArn=arn))
        if str(detail.get("deviceType")) != "QPU" or str(detail.get("deviceStatus")) != "ONLINE":
            continue
        queue_raw = detail.get("deviceQueueInfo", [])
        queue_info: tuple[Mapping[str, str], ...]
        if isinstance(queue_raw, list):
            queue_info = tuple(
                {
                    "queue": str(row.get("queue", "")),
                    "queuePriority": str(row.get("queuePriority", "")),
                    "queueSize": str(row.get("queueSize", "")),
                }
                for row in queue_raw
                if isinstance(row, Mapping)
            )
        else:
            queue_info = ()
        capabilities = detail.get("deviceCapabilities", "")
        snapshot = {
            "deviceArn": arn,
            "deviceName": str(detail.get("deviceName") or summary.get("deviceName") or ""),
            "providerName": str(detail.get("providerName") or summary.get("providerName") or ""),
            "deviceStatus": str(detail.get("deviceStatus")),
            "deviceType": str(detail.get("deviceType")),
            "deviceQueueInfo": list(queue_info),
            "deviceCapabilitiesDigest": _digest(capabilities),
        }
        candidates.append(
            BraketQPUCandidate(
                region=region,
                device_arn=arn,
                device_name=snapshot["deviceName"],
                provider_name=snapshot["providerName"],
                device_status="ONLINE",
                device_type="QPU",
                queue_info=queue_info,
                device_capabilities_digest=snapshot["deviceCapabilitiesDigest"],
                device_snapshot_digest=_digest(snapshot),
            )
        )

    return tuple(sorted(candidates, key=lambda row: (row.provider_name.lower(), row.device_name.lower(), row.device_arn)))


def candidates_as_dict(candidates: tuple[BraketQPUCandidate, ...]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "evidence_class": "read_only_braket_qpu_discovery_not_hardware_execution",
        "candidate_count": len(candidates),
        "candidates": [asdict(row) for row in candidates],
        "claim_control": (
            "Device discovery is read-only access metadata. It is not a reservation, paid task, QPU execution, provider validation, "
            "or mission-readiness evidence. Current pricing and execution-window availability must be checked separately before submission."
        ),
    }

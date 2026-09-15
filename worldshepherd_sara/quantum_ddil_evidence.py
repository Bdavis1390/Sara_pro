"""DDIL/deferred-synchronization custody for Worldshepherd quantum evidence.

Mission evidence may be created while disconnected, intermittent or bandwidth-limited.
The original local identity must survive later provider synchronization. Provider
acknowledgements are additional provenance and must never replace or regenerate the
locally timestamped artifact/configuration identities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


_SHA = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_ALLOWED_SYNC = {"deferred", "acknowledged", "conflict"}


def sha256_bytes(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256_bytes(encoded)


def _valid_utc(value: str) -> bool:
    if not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DDILCustodyRecord:
    custody_id: str
    project_id: str
    node_id: str
    local_sequence: int
    collected_utc: str
    local_artifact_digest: str
    local_configuration_digest: str
    campaign_gate_id: str
    sync_state: str = "deferred"
    provider_or_service: str | None = None
    provider_ack_id: str | None = None
    provider_artifact_digest: str | None = None
    synchronized_utc: str | None = None
    conflict_reason: str | None = None
    claim_control: str = (
        "The local custody identity is authoritative for what the node observed and hashed while DDIL. "
        "Later provider acknowledgement augments provenance and cannot rewrite the original local artifact/configuration identity."
    )


@dataclass(frozen=True)
class DDILCustodyDecision:
    accepted: bool
    reasons: tuple[str, ...]
    record_digest: str
    identity_preserved: bool
    claim_control: str


def custody_identity_payload(record: DDILCustodyRecord) -> dict[str, Any]:
    """Fields that must never change after local custody is created."""
    return {
        "custody_id": record.custody_id,
        "project_id": record.project_id,
        "node_id": record.node_id,
        "local_sequence": record.local_sequence,
        "collected_utc": record.collected_utc,
        "local_artifact_digest": record.local_artifact_digest,
        "local_configuration_digest": record.local_configuration_digest,
        "campaign_gate_id": record.campaign_gate_id,
    }


def custody_identity_digest(record: DDILCustodyRecord) -> str:
    return _digest_json(custody_identity_payload(record))


def custody_record_digest(record: DDILCustodyRecord) -> str:
    return _digest_json(asdict(record))


def create_ddil_custody(
    artifact_path: str | Path,
    *,
    project_id: str,
    node_id: str,
    local_sequence: int,
    local_configuration_digest: str,
    campaign_gate_id: str,
    collected_utc: str | None = None,
) -> DDILCustodyRecord:
    path = Path(artifact_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("DDIL artifact must exist and be non-empty")
    if local_sequence <= 0:
        raise ValueError("local_sequence must be positive")
    if not _SHA.fullmatch(local_configuration_digest):
        raise ValueError("local_configuration_digest must be sha256")
    timestamp = collected_utc or utc_now_z()
    if not _valid_utc(timestamp):
        raise ValueError("collected_utc must be a valid UTC timestamp ending in Z")
    if not project_id.strip() or not node_id.strip() or not campaign_gate_id.strip():
        raise ValueError("project_id, node_id and campaign_gate_id are required")

    artifact_digest = sha256_bytes(path.read_bytes())
    seed = {
        "project_id": project_id,
        "node_id": node_id,
        "local_sequence": local_sequence,
        "collected_utc": timestamp,
        "local_artifact_digest": artifact_digest,
        "local_configuration_digest": local_configuration_digest,
        "campaign_gate_id": campaign_gate_id,
    }
    custody_id = "WS-DDIL-" + sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return DDILCustodyRecord(
        custody_id=custody_id,
        project_id=project_id,
        node_id=node_id,
        local_sequence=local_sequence,
        collected_utc=timestamp,
        local_artifact_digest=artifact_digest,
        local_configuration_digest=local_configuration_digest,
        campaign_gate_id=campaign_gate_id,
    )


def validate_ddil_custody(
    record: DDILCustodyRecord,
    *,
    artifact_path: str | Path | None = None,
    expected_identity_digest: str | None = None,
) -> DDILCustodyDecision:
    reasons: list[str] = []
    if not record.custody_id.strip() or not record.project_id.strip() or not record.node_id.strip() or not record.campaign_gate_id.strip():
        reasons.append("custody/project/node/campaign identities are required")
    if record.local_sequence <= 0:
        reasons.append("local_sequence must be positive")
    if not _valid_utc(record.collected_utc):
        reasons.append("collected_utc must be valid UTC ending in Z")
    if not _SHA.fullmatch(record.local_artifact_digest):
        reasons.append("local_artifact_digest must be sha256")
    if not _SHA.fullmatch(record.local_configuration_digest):
        reasons.append("local_configuration_digest must be sha256")
    if record.sync_state not in _ALLOWED_SYNC:
        reasons.append("sync_state must be deferred, acknowledged or conflict")

    if record.sync_state == "deferred":
        if any((record.provider_ack_id, record.provider_artifact_digest, record.synchronized_utc, record.conflict_reason)):
            reasons.append("deferred record cannot contain provider acknowledgement/conflict fields")
    elif record.sync_state == "acknowledged":
        if not record.provider_or_service or not record.provider_ack_id or not record.synchronized_utc:
            reasons.append("acknowledged record requires provider/service, acknowledgement ID and synchronized_utc")
        if not _valid_utc(record.synchronized_utc or ""):
            reasons.append("synchronized_utc must be valid UTC ending in Z")
        if not _SHA.fullmatch(record.provider_artifact_digest or ""):
            reasons.append("acknowledged record requires provider_artifact_digest sha256")
        elif record.provider_artifact_digest.lower() != record.local_artifact_digest.lower():
            reasons.append("provider artifact digest conflicts with the original local artifact identity")
    elif record.sync_state == "conflict":
        if not record.provider_or_service or not record.provider_ack_id or not record.synchronized_utc or not record.conflict_reason:
            reasons.append("conflict record requires provider/service, acknowledgement ID, synchronized_utc and conflict_reason")
        if not _valid_utc(record.synchronized_utc or ""):
            reasons.append("synchronized_utc must be valid UTC ending in Z")

    if artifact_path is not None:
        path = Path(artifact_path)
        if not path.is_file() or path.stat().st_size == 0:
            reasons.append("bound local artifact does not exist or is empty")
        else:
            actual = sha256_bytes(path.read_bytes())
            if actual.lower() != record.local_artifact_digest.lower():
                reasons.append("bound local artifact no longer matches original DDIL digest")

    identity_digest = custody_identity_digest(record)
    identity_preserved = True
    if expected_identity_digest is not None:
        if not _SHA.fullmatch(expected_identity_digest):
            reasons.append("expected_identity_digest must be sha256")
            identity_preserved = False
        elif identity_digest.lower() != expected_identity_digest.lower():
            reasons.append("immutable DDIL custody identity changed after local creation")
            identity_preserved = False

    return DDILCustodyDecision(
        accepted=not reasons,
        reasons=tuple(reasons),
        record_digest=custody_record_digest(record),
        identity_preserved=identity_preserved and not any("identity changed" in reason for reason in reasons),
        claim_control=(
            "Accepted custody proves local hash/configuration identity continuity and synchronization bookkeeping only. "
            "It does not establish scientific validity or satisfy a mission evidence gate by itself."
        ),
    )


def acknowledge_delayed_sync(
    record: DDILCustodyRecord,
    *,
    provider_or_service: str,
    provider_ack_id: str,
    provider_artifact_digest: str,
    synchronized_utc: str | None = None,
) -> DDILCustodyRecord:
    """Add provider acknowledgement without changing immutable local identity fields.

    A digest mismatch is retained as an explicit conflict state rather than silently
    replacing the locally observed artifact identity.
    """
    if record.sync_state != "deferred":
        raise ValueError("only a deferred custody record may be synchronized")
    if not provider_or_service.strip() or not provider_ack_id.strip():
        raise ValueError("provider/service and acknowledgement ID are required")
    if not _SHA.fullmatch(provider_artifact_digest):
        raise ValueError("provider_artifact_digest must be sha256")
    timestamp = synchronized_utc or utc_now_z()
    if not _valid_utc(timestamp):
        raise ValueError("synchronized_utc must be valid UTC ending in Z")

    conflict = provider_artifact_digest.lower() != record.local_artifact_digest.lower()
    return replace(
        record,
        sync_state="conflict" if conflict else "acknowledged",
        provider_or_service=provider_or_service,
        provider_ack_id=provider_ack_id,
        provider_artifact_digest=provider_artifact_digest,
        synchronized_utc=timestamp,
        conflict_reason=(
            "provider-reported artifact digest differs from original local DDIL artifact digest; local identity preserved"
            if conflict else None
        ),
    )

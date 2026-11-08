"""SCITT-oriented serializer for deterministic WS-CAE continuity snapshots.

Serialization and validation only. No keys, signatures, transactions, wallet
access, asset movement, or transparency-service administration.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from .continuity_catalog import _snapshot_id
from .continuity_validation import valid_content_id, valid_date, valid_datetime

SPEC = "WS-CAE-SCITT-CONTINUITY-SNAPSHOT-1"
MEDIA_TYPE = "application/vnd.ws-cae.continuity-snapshot+json"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validated_snapshot(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if snapshot.get("spec") != "WS-CAE-CONTINUITY-SNAPSHOT-1":
        raise ValueError("snapshot spec is not recognized")
    if not valid_date(str(snapshot.get("as_of", ""))):
        raise ValueError("snapshot as_of must be a real YYYY-MM-DD date")
    manifests = snapshot.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        raise ValueError("snapshot manifests must be a non-empty array")
    if snapshot.get("manifest_count") != len(manifests):
        raise ValueError("snapshot manifest_count does not match manifests")

    content_ids: list[str] = []
    seen_subjects: set[str] = set()
    for index, row in enumerate(manifests):
        if not isinstance(row, dict):
            raise ValueError(f"snapshot manifests[{index}] must be an object")
        subject = str(row.get("subject", "")).strip()
        if not subject:
            raise ValueError(f"snapshot manifests[{index}] subject must be non-empty")
        key = subject.lower()
        if key in seen_subjects:
            raise ValueError(f"duplicate snapshot subject: {subject}")
        seen_subjects.add(key)
        content_id = str(row.get("content_id", ""))
        if not valid_content_id(content_id):
            raise ValueError(f"snapshot manifests[{index}] content_id is not canonical SHA-256")
        content_ids.append(content_id)
        if row.get("valid") is not True:
            raise ValueError(f"snapshot manifests[{index}] is not valid")

    expected_id = _snapshot_id(content_ids)
    claimed_id = str(snapshot.get("snapshot_id", ""))
    if claimed_id != expected_id:
        raise ValueError("snapshot_id does not match manifest content identifiers")
    if snapshot.get("all_valid") is not True:
        raise ValueError("snapshot all_valid must be true")
    return json.loads(json.dumps(snapshot, sort_keys=True))


def build_snapshot_statement(
    snapshot: dict,
    issuer: str,
    observed_at: str | None = None,
) -> dict:
    issuer = issuer.strip()
    if not issuer:
        raise ValueError("issuer must be non-empty")
    normalized = _validated_snapshot(snapshot)
    timestamp = observed_at or _now()
    if not valid_datetime(timestamp):
        raise ValueError("observed_at must be a timezone-aware ISO-8601 datetime")
    return {
        "spec": SPEC,
        "media_type": MEDIA_TYPE,
        "issuer": issuer,
        "observed_at": timestamp,
        "snapshot_id": normalized["snapshot_id"],
        "snapshot": normalized,
    }


def verify_snapshot_statement(statement: dict) -> bool:
    try:
        if statement.get("spec") != SPEC or statement.get("media_type") != MEDIA_TYPE:
            return False
        issuer = str(statement.get("issuer", "")).strip()
        if not issuer or not valid_datetime(str(statement.get("observed_at", ""))):
            return False
        normalized = _validated_snapshot(statement["snapshot"])
        return statement.get("snapshot_id") == normalized["snapshot_id"]
    except (KeyError, TypeError, ValueError):
        return False

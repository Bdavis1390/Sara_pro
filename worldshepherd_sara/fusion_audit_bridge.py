"""Map fusion replay evidence into the existing SARA audit event shape.

This bridge is intentionally non-mutating: it returns dictionaries compatible
with the SARA audit schema but does not write files, call server endpoints, or
change admin/operator authority.  A later reviewed integration can choose how
to persist these mapped events.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Iterable, List

from worldshepherd_sara.fusion_control import AuditRecord


DEFAULT_FUSION_AUDIT_ACTOR = "SARA_FUSION_SIM"


def fusion_record_to_sara_event(
    record: AuditRecord,
    *,
    actor: str = DEFAULT_FUSION_AUDIT_ACTOR,
) -> Dict[str, Any]:
    actor = actor.strip()
    if not actor:
        raise ValueError("audit_actor_missing")
    if actor.lower() in {"admin", "operator", "sspadawanzz_admin"}:
        raise ValueError("fusion_bridge_cannot_impersonate_privileged_actor")

    return {
        "ts": float(record.timestamp),
        "event": f"fusion.{record.event}",
        "actor": actor,
        "payload": {
            "fusion_sequence": int(record.sequence),
            "fusion_previous_hash": record.previous_hash,
            "fusion_record_hash": record.record_hash,
            "fusion_payload": dict(record.payload),
        },
    }


def fusion_records_to_sara_events(
    records: Iterable[AuditRecord],
    *,
    actor: str = DEFAULT_FUSION_AUDIT_ACTOR,
) -> List[Dict[str, Any]]:
    events = [fusion_record_to_sara_event(record, actor=actor) for record in records]
    for expected_sequence, event in enumerate(events):
        sequence = event["payload"]["fusion_sequence"]
        if sequence != expected_sequence:
            raise ValueError(
                f"fusion_audit_sequence_not_contiguous:{expected_sequence}:{sequence}"
            )
    return events

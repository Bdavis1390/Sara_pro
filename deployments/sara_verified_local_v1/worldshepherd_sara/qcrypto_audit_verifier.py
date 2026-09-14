from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA, QCRYPTO_EVENT_SCHEMA


_EXPECTED_EVENTS = {
    "qcrypto_echo_state": "ECHO",
    "qcrypto_prime_state": "PRIME",
    "qcrypto_sara_state": "SARA",
    "qcrypto_overwatch_state": "OVERWATCH",
}
_FORBIDDEN_TRUE_FIELDS = (
    "migration_executed",
    "execution_authority",
    "live_value_authorized",
    "federal_compliance_established",
    "ws_cae_conformance_established",
)
_COMMON_FIELDS = (
    "schema",
    "source_schema",
    "decision_digest",
    "asset_id",
    "priority",
    "human_approval_required",
    "migration_executed",
    "execution_authority",
    "live_value_authorized",
    "federal_compliance_established",
    "ws_cae_conformance_established",
    "claim_boundary",
    "correlation_id",
)


@dataclass(frozen=True)
class QCryptoAuditVerification:
    decision_digest: str
    verdict: str
    complete: bool
    consistent: bool
    stages_present: tuple[str, ...]
    missing_stages: tuple[str, ...]
    matching_record_count: int
    logical_event_count: int
    reasons: tuple[str, ...]
    execution_authority: bool = False
    live_value_authorized: bool = False
    federal_compliance_established: bool = False
    ws_cae_conformance_established: bool = False
    claim_boundary: str = (
        "Internal SARA audit-chain reconstruction only; does not establish migration execution, "
        "live-value authorization, Federal compliance, or WS-CAE conformance."
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _record_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return ("MALFORMED",)
    return (
        record.get("event"),
        record.get("actor"),
        payload.get("stage"),
        payload.get("state"),
        *tuple(payload.get(field) for field in _COMMON_FIELDS),
    )


def verify_qcrypto_audit_chain(
    records: list[dict[str, Any]],
    *,
    decision_digest: str,
) -> QCryptoAuditVerification:
    """Reconstruct one QCRYPTO decision from SARA audit records.

    Verification is intentionally local and claims-controlled. It checks that
    ECHO, PRIME, SARA, and OVERWATCH records for the same deterministic decision
    digest agree on common governance fields and preserve all non-authority
    boundaries. At-least-once replay duplicates are tolerated when identical.
    """
    if not isinstance(decision_digest, str) or not decision_digest.startswith("sha256:"):
        raise ValueError("decision_digest must be a sha256-prefixed string")

    matching: list[dict[str, Any]] = []
    reasons: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        payload = record.get("payload")
        if isinstance(payload, dict) and payload.get("decision_digest") == decision_digest:
            matching.append(record)

    if not matching:
        return QCryptoAuditVerification(
            decision_digest=decision_digest,
            verdict="NO_MATCHING_AUDIT_EVIDENCE",
            complete=False,
            consistent=False,
            stages_present=(),
            missing_stages=tuple(_EXPECTED_EVENTS.values()),
            matching_record_count=0,
            logical_event_count=0,
            reasons=("No SARA audit records matched the supplied decision digest.",),
        )

    # Deduplicate exact at-least-once replays by stable outbox event ID. If a
    # stable ID reappears with divergent content, preserve both and flag it.
    by_outbox_id: dict[str, tuple[tuple[Any, ...], dict[str, Any]]] = {}
    logical_records: list[dict[str, Any]] = []
    for record in matching:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            logical_records.append(record)
            continue
        outbox_id = payload.get("_outbox_event_id")
        if not isinstance(outbox_id, str) or not outbox_id:
            reasons.append("Matching record is missing a stable SARA outbox event ID.")
            logical_records.append(record)
            continue
        signature = _record_signature(record)
        prior = by_outbox_id.get(outbox_id)
        if prior is None:
            by_outbox_id[outbox_id] = (signature, record)
            logical_records.append(record)
        elif prior[0] != signature:
            reasons.append(f"Stable outbox event ID {outbox_id} has divergent replay content.")
            logical_records.append(record)

    stage_records: dict[str, list[dict[str, Any]]] = {
        stage: [] for stage in _EXPECTED_EVENTS.values()
    }
    common_reference: dict[str, Any] | None = None
    actor_reference: Any = None

    for record in logical_records:
        event = record.get("event")
        payload = record.get("payload")
        if event not in _EXPECTED_EVENTS or not isinstance(payload, dict):
            reasons.append("Matching audit record has an unexpected event name or malformed payload.")
            continue

        expected_stage = _EXPECTED_EVENTS[event]
        if payload.get("stage") != expected_stage:
            reasons.append(
                f"Event {event} has stage {payload.get('stage')!r}; expected {expected_stage}."
            )
            continue
        stage_records[expected_stage].append(record)

        if payload.get("schema") != QCRYPTO_EVENT_SCHEMA:
            reasons.append(f"Stage {expected_stage} has an unsupported event schema.")
        if payload.get("source_schema") != QCRYPTO_AUDIT_SCHEMA:
            reasons.append(f"Stage {expected_stage} has an unsupported source schema.")
        if payload.get("human_approval_required") is not True:
            reasons.append(f"Stage {expected_stage} does not preserve the human approval gate.")
        for field in _FORBIDDEN_TRUE_FIELDS:
            if payload.get(field) is not False:
                reasons.append(f"Stage {expected_stage} illegally promotes {field}.")
        if payload.get("_delivery_semantics") != "AT_LEAST_ONCE":
            reasons.append(f"Stage {expected_stage} lacks native SARA delivery semantics.")

        common = {field: payload.get(field) for field in _COMMON_FIELDS}
        if common_reference is None:
            common_reference = common
            actor_reference = record.get("actor")
        else:
            for field in _COMMON_FIELDS:
                if common.get(field) != common_reference.get(field):
                    reasons.append(f"Cross-stage field {field} is inconsistent.")
            if record.get("actor") != actor_reference:
                reasons.append("Cross-stage actor identity is inconsistent.")

    # Multiple submissions of the exact same decision digest are acceptable only
    # when the stage-specific records agree with each other.
    for stage, items in stage_records.items():
        if len(items) > 1:
            signatures = {_record_signature(item) for item in items}
            if len(signatures) > 1:
                reasons.append(f"Stage {stage} has divergent records for the same decision digest.")

    present = tuple(stage for stage, items in stage_records.items() if items)
    missing = tuple(stage for stage, items in stage_records.items() if not items)
    complete = not missing
    consistent = not reasons

    if complete and consistent:
        verdict = "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    elif not complete and consistent:
        verdict = "INCOMPLETE_AUDIT_CHAIN"
    else:
        verdict = "INCONSISTENT_AUDIT_CHAIN"

    if missing:
        reasons.append("Missing required stages: " + ", ".join(missing))

    return QCryptoAuditVerification(
        decision_digest=decision_digest,
        verdict=verdict,
        complete=complete,
        consistent=consistent,
        stages_present=present,
        missing_stages=missing,
        matching_record_count=len(matching),
        logical_event_count=len(logical_records),
        reasons=tuple(reasons),
    )

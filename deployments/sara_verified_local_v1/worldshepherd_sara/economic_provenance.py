from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from .economic_ledger import EconomicLedgerRecord
from .event_outbox import queue_event_outbox_patch
from .limits import validate_json_resource


ECONOMIC_PROVENANCE_SCHEMA = "WS-ECONOMIC-PROVENANCE-G3-V1"
EconomicProvenancePhase = Literal[
    "INTENT_RECORDED",
    "DECISION_RECORDED",
    "AUTHORIZATION_RECORDED",
    "DRY_RUN_CONSUMED",
    "FAILED",
]


class EconomicProvenanceError(ValueError):
    pass


def _stable_event_id(record: EconomicLedgerRecord, phase: EconomicProvenancePhase) -> str:
    material = json.dumps(
        {
            "schema": ECONOMIC_PROVENANCE_SCHEMA,
            "intent_id": record.intent_id,
            "intent_sha256": record.intent_sha256,
            "phase": phase,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(material).hexdigest()
    return f"SARA-EVENT-ECON-{phase}-{digest}"


def _base_payload(
    record: EconomicLedgerRecord,
    *,
    phase: EconomicProvenancePhase,
) -> dict[str, Any]:
    return {
        "schema": ECONOMIC_PROVENANCE_SCHEMA,
        "phase": phase,
        "intent_id": record.intent_id,
        "intent_sha256": record.intent_sha256,
        "policy_id": record.policy_id,
        "policy_sha256": record.policy_sha256,
        "session_id": record.session_id,
        "protocol": record.protocol,
        "network": record.network,
        "asset": record.asset,
        "payee": record.payee,
        "amount": record.amount,
        "mode": record.mode,
        "raw_provider_content_included": False,
        "wallet_credentials_included": False,
        "private_signing_material_included": False,
    }


def build_economic_provenance_event(
    record: EconomicLedgerRecord,
    *,
    phase: EconomicProvenancePhase,
) -> dict[str, Any]:
    """Build one stable, transport-neutral economic provenance event.

    The event intentionally excludes wallet credentials, private signing
    material, raw provider content, and any payment-instrument secret.
    """

    payload = _base_payload(record, phase=phase)
    actor = "SARA"

    if phase == "INTENT_RECORDED":
        payload.update(
            {
                "nonce_sha256": hashlib.sha256(record.nonce.encode("utf-8")).hexdigest(),
                "recorded_at": record.recorded_at,
            }
        )
    elif phase == "DECISION_RECORDED":
        decision = record.decision()
        if decision is None or record.decision_status not in {"ALLOWED", "DENIED"}:
            raise EconomicProvenanceError("economic decision has not been durably recorded")
        payload.update(
            {
                "decision_status": record.decision_status,
                "disposition": decision.disposition,
                "reasons": list(decision.reasons),
                "spent_before": str(decision.spent_before),
                "remaining_budget_after": str(decision.remaining_budget_after),
                "decision_at": record.decision_at,
            }
        )
    elif phase == "AUTHORIZATION_RECORDED":
        if record.authorization_status == "NOT_BOUND":
            raise EconomicProvenanceError("economic authorization result has not been recorded")
        actor = "PRIME_SENTINEL"
        payload.update(
            {
                "authorization_status": record.authorization_status,
                "authorization_ref": record.authorization_ref,
                "authorization_digest_sha256": record.authorization_digest_sha256,
                "authorization_nonce_sha256": (
                    hashlib.sha256(record.authorization_nonce.encode("utf-8")).hexdigest()
                    if record.authorization_nonce
                    else None
                ),
                "authorization_at": record.authorization_at,
            }
        )
    elif phase == "DRY_RUN_CONSUMED":
        if record.consumption_status != "DRY_RUN_CONSUMED":
            raise EconomicProvenanceError("dry-run economic intent has not been consumed")
        payload.update(
            {
                "consumption_status": record.consumption_status,
                "adapter_receipt_ref": record.adapter_receipt_ref,
                "consumed_at": record.consumed_at,
                "external_settlement_claimed": False,
            }
        )
    elif phase == "FAILED":
        if not record.failure_code:
            raise EconomicProvenanceError("economic failure has not been recorded")
        payload.update(
            {
                "failure_code": record.failure_code,
                "failed_at": record.failed_at,
            }
        )
    else:
        raise EconomicProvenanceError("unsupported economic provenance phase")

    payload = validate_json_resource(payload)
    return {
        "event_id": _stable_event_id(record, phase),
        "event": "economic_provenance",
        "actor": actor,
        "payload": payload,
    }


def queue_economic_provenance_patch(
    registry: dict[str, Any],
    record: EconomicLedgerRecord,
    *,
    phase: EconomicProvenancePhase,
) -> tuple[dict[str, Any], str]:
    event = build_economic_provenance_event(record, phase=phase)
    return queue_event_outbox_patch(
        registry,
        event=event["event"],
        actor=event["actor"],
        payload=event["payload"],
        event_id=event["event_id"],
    )

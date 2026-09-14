from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Dict, Iterable, Mapping, Optional

READ_TICKET_SCHEMA = "worldshepherd.connector.read-ticket.v1"
READ_RECEIPT_SCHEMA = "worldshepherd.connector.read-receipt.v1"
VALID_RECEIPT_STATUS = {"success", "empty", "error"}


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _value_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def verify_read_ticket(ticket: Mapping[str, Any]) -> bool:
    if ticket.get("schema") != READ_TICKET_SCHEMA:
        return False
    if ticket.get("write_enabled") is not False:
        return False
    if ticket.get("execution_mode") != "host_connector_handoff":
        return False
    if ticket.get("credential_handling") != "outside_sara_broker":
        return False
    for field in ("connector_id", "action", "actor", "data_class"):
        if not isinstance(ticket.get(field), str) or not ticket.get(field):
            return False
    issued_at = ticket.get("issued_at")
    if not isinstance(issued_at, (int, float)) or issued_at <= 0:
        return False
    if not _valid_sha256(ticket.get("policy_envelope_sha256")):
        return False
    supplied = ticket.get("sha256")
    if not _valid_sha256(supplied):
        return False
    unsigned = dict(ticket)
    unsigned.pop("sha256", None)
    expected = _canonical_sha256(unsigned)
    return hmac.compare_digest(str(supplied), expected)


def seal_read_receipt(
    *,
    ticket: Mapping[str, Any],
    status: str,
    result_sha256: str,
    host_result_id: str = "",
    source_refs: Optional[Iterable[str]] = None,
    evidence_refs: Optional[Iterable[str]] = None,
    completed_at: Optional[float] = None,
) -> Dict[str, Any]:
    """Bind a host-reported result digest to a verified authorization ticket.

    Raw connector results, credentials, and external identifiers are not embedded.
    Source/evidence identifiers are hashed before entering the receipt. The receipt
    proves chain integrity, not correctness of the external service or host report.
    """
    if not verify_read_ticket(ticket):
        raise ValueError("invalid read handoff ticket")
    if status not in VALID_RECEIPT_STATUS:
        raise ValueError("invalid receipt status")
    if not _valid_sha256(result_sha256):
        raise ValueError("result_sha256 must be a 64-character SHA-256 hex digest")

    finished = time.time() if completed_at is None else float(completed_at)
    if finished < float(ticket["issued_at"]):
        raise ValueError("receipt completion cannot predate ticket issuance")

    source_hashes = [_value_sha256(str(value)) for value in (source_refs or [])]
    evidence_hashes = [_value_sha256(str(value)) for value in (evidence_refs or [])]
    host_result_hash = _value_sha256(str(host_result_id)) if host_result_id else None

    payload: Dict[str, Any] = {
        "schema": READ_RECEIPT_SCHEMA,
        "ticket_sha256": ticket["sha256"],
        "policy_envelope_sha256": ticket["policy_envelope_sha256"],
        "connector_id": ticket["connector_id"],
        "action": ticket["action"],
        "actor": ticket["actor"],
        "data_class": ticket["data_class"],
        "status": status,
        "result_sha256": result_sha256,
        "host_result_id_sha256": host_result_hash,
        "source_ref_sha256s": source_hashes,
        "evidence_ref_sha256s": evidence_hashes,
        "execution_attestation": "host_reported",
        "raw_result_embedded": False,
        "raw_external_identifiers_embedded": False,
        "credential_material_embedded": False,
        "completed_at": finished,
    }
    payload["sha256"] = _canonical_sha256(payload)
    return payload


def verify_read_receipt(
    receipt: Mapping[str, Any],
    *,
    ticket: Mapping[str, Any],
    result_bytes: Optional[bytes] = None,
) -> bool:
    if not verify_read_ticket(ticket):
        return False
    if receipt.get("schema") != READ_RECEIPT_SCHEMA:
        return False
    if receipt.get("execution_attestation") != "host_reported":
        return False
    if receipt.get("raw_result_embedded") is not False:
        return False
    if receipt.get("raw_external_identifiers_embedded") is not False:
        return False
    if receipt.get("credential_material_embedded") is not False:
        return False
    if receipt.get("status") not in VALID_RECEIPT_STATUS:
        return False
    if receipt.get("ticket_sha256") != ticket.get("sha256"):
        return False
    if receipt.get("policy_envelope_sha256") != ticket.get("policy_envelope_sha256"):
        return False
    for field in ("connector_id", "action", "actor", "data_class"):
        if receipt.get(field) != ticket.get(field):
            return False

    completed_at = receipt.get("completed_at")
    if not isinstance(completed_at, (int, float)):
        return False
    if completed_at < float(ticket["issued_at"]):
        return False

    host_result_hash = receipt.get("host_result_id_sha256")
    if host_result_hash is not None and not _valid_sha256(host_result_hash):
        return False
    for list_field in ("source_ref_sha256s", "evidence_ref_sha256s"):
        values = receipt.get(list_field)
        if not isinstance(values, list) or not all(_valid_sha256(value) for value in values):
            return False

    supplied = receipt.get("sha256")
    if not _valid_sha256(supplied) or not _valid_sha256(receipt.get("result_sha256")):
        return False
    unsigned = dict(receipt)
    unsigned.pop("sha256", None)
    if not hmac.compare_digest(str(supplied), _canonical_sha256(unsigned)):
        return False
    if result_bytes is not None:
        result_digest = hashlib.sha256(result_bytes).hexdigest()
        if not hmac.compare_digest(str(receipt.get("result_sha256")), result_digest):
            return False
    return True

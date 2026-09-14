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
    """Bind a host-reported read result to a verified authorization ticket.

    The receipt contains hashes and identifiers only. It does not prove that the
    external service executed correctly, and it must not contain credentials or
    raw connector result content.
    """
    if not verify_read_ticket(ticket):
        raise ValueError("invalid read handoff ticket")
    if status not in VALID_RECEIPT_STATUS:
        raise ValueError("invalid receipt status")
    if not _valid_sha256(result_sha256):
        raise ValueError("result_sha256 must be a 64-character SHA-256 hex digest")

    sources = [str(value) for value in (source_refs or [])]
    evidence = [str(value) for value in (evidence_refs or [])]
    payload: Dict[str, Any] = {
        "schema": READ_RECEIPT_SCHEMA,
        "ticket_sha256": ticket["sha256"],
        "policy_envelope_sha256": ticket["policy_envelope_sha256"],
        "connector_id": ticket.get("connector_id"),
        "action": ticket.get("action"),
        "actor": ticket.get("actor"),
        "data_class": ticket.get("data_class"),
        "status": status,
        "result_sha256": result_sha256,
        "host_result_id": str(host_result_id),
        "source_refs": sources,
        "evidence_refs": evidence,
        "execution_attestation": "host_reported",
        "raw_result_embedded": False,
        "credential_material_embedded": False,
        "completed_at": time.time() if completed_at is None else float(completed_at),
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

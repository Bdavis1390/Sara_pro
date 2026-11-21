"""Scientific execution event inclusion in an ECHO-signed checkpoint.

This module reuses the canonical SARA/ECHO event digest and Ed25519 checkpoint
verifier. It is a standalone integration candidate, not a SARA ingestion endpoint,
PRIME authorization verifier, third-party witness, or scientific proof.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from worldshepherd_sara.echo_checkpoint_verify import (
    EchoCheckpointVerificationError,
    verify_bundle,
    verify_chain,
)
from worldshepherd_sara.echo_event_store import EchoEventStoreError, semantic_sha256
from worldshepherd_sara.models import AuditRecord

from bounded_execution import (
    ExecutionCustodyError,
    canonical,
    verify_receipt,
)

SCIENCE_EVENT_SCHEMA = "WS-SCIENTIFIC-EXECUTION-SEMANTIC-V1"
SCIENCE_WITNESS_SCHEMA = "WS-SCIENTIFIC-ECHO-WITNESS-V1"
SCIENCE_EVENT = "SCIENTIFIC_EXECUTION_LOCAL_REPRODUCED"
SCIENCE_ACTOR = "WS_SCIENCE_GATE_REFERENCE"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
CLAIM_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
PAYLOAD_FIELDS = frozenset({
    "schema", "claim_id", "prereg_sha256", "run_id", "receipt_sha256",
    "config_sha256", "input_sha256", "output_sha256", "source_sha256",
    "execution_custody_state", "prime_authorization_verified",
    "preexecution_freeze_verified", "_outbox_event_id", "_delivery_semantics",
})


class ScientificEchoWitnessError(ValueError):
    pass


def _expect_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise ScientificEchoWitnessError(f"{label} must be lowercase sha256")
    return value


def _payload(receipt: dict[str, Any], claim_id: str, prereg_sha256: str) -> dict[str, Any]:
    if not isinstance(claim_id, str) or CLAIM_ID.fullmatch(claim_id) is None:
        raise ScientificEchoWitnessError("invalid claim ID")
    prereg_sha256 = _expect_digest(prereg_sha256, "preregistration digest")
    if not isinstance(receipt, dict):
        raise ScientificEchoWitnessError("invalid receipt")
    run_id = receipt.get("run_id")
    if not isinstance(run_id, str):
        raise ScientificEchoWitnessError("receipt lacks run ID")
    receipt_sha256 = _expect_digest(receipt.get("receipt_sha256"), "receipt digest")
    fields = {"schema": SCIENCE_EVENT_SCHEMA, "claim_id": claim_id,
              "prereg_sha256": prereg_sha256, "receipt_sha256": receipt_sha256}
    stable_id = hashlib.sha256(
        b"WS-SCIENTIFIC-ECHO-EXECUTION-V1\0" + canonical(fields)
    ).hexdigest()[:40]
    return {
        **fields,
        "run_id": run_id,
        "config_sha256": _expect_digest(receipt.get("configuration", {}).get("sha256"), "config digest"),
        "input_sha256": _expect_digest(receipt.get("input", {}).get("sha256"), "input digest"),
        "output_sha256": _expect_digest(receipt.get("output", {}).get("sha256"), "output digest"),
        "source_sha256": _expect_digest(receipt.get("source_sha256"), "source digest"),
        "execution_custody_state": "SELF_REPORTED_LOCALLY_REPRODUCED",
        "prime_authorization_verified": False,
        "preexecution_freeze_verified": False,
        "_outbox_event_id": f"SARA-EVENT-SCIENCE-{stable_id}",
        "_delivery_semantics": "AT_LEAST_ONCE",
    }


def create_scientific_event(
    root: str | Path,
    receipt: dict[str, Any],
    *,
    claim_id: str,
    prereg_sha256: str,
) -> dict[str, Any]:
    """Construct a bounded SARA-shaped audit record after local recomputation.

    This only creates an event *candidate*. It does not submit it to SARA/ECHO.
    """
    try:
        checked = verify_receipt(Path(root), receipt)
    except (ExecutionCustodyError, OSError, ValueError, TypeError) as exc:
        raise ScientificEchoWitnessError("local execution receipt verification failed") from exc
    if checked.get("status") != "PASS":
        raise ScientificEchoWitnessError("local execution receipt is not reproducible")
    payload = _payload(receipt, claim_id, prereg_sha256)
    return AuditRecord.create(
        event=SCIENCE_EVENT,
        actor=SCIENCE_ACTOR,
        payload=payload,
    ).model_dump(mode="json")


def verify_scientific_echo_witness(
    root: str | Path,
    receipt: dict[str, Any],
    record: dict[str, Any],
    checkpoint_bundles: list[dict[str, Any]],
    *,
    expected_claim_id: str,
    expected_prereg_sha256: str,
    expected_checkpoint_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    """Check exact event inclusion under a separately pinned checkpoint key.

    Callers MUST obtain the preregistration digest and trusted signing key
    fingerprint independently of this evidence package. This function cannot
    verify when or where those values were pinned.
    """
    if not isinstance(record, dict):
        raise ScientificEchoWitnessError("audit record must be an object")
    try:
        checked = verify_receipt(Path(root), receipt)
    except (ExecutionCustodyError, OSError, ValueError, TypeError) as exc:
        raise ScientificEchoWitnessError("execution receipt is not locally reproducible") from exc
    if checked.get("status") != "PASS":
        raise ScientificEchoWitnessError("execution receipt is not locally reproducible")

    try:
        audit = AuditRecord(**record)
        payload = audit.payload
        expected_payload = _payload(receipt, expected_claim_id, expected_prereg_sha256)
        if audit.event != SCIENCE_EVENT or audit.actor != SCIENCE_ACTOR:
            raise ScientificEchoWitnessError("unexpected event/actor identity")
        if set(payload) != PAYLOAD_FIELDS or payload != expected_payload:
            raise ScientificEchoWitnessError("scientific event semantic payload mismatch")
        semantic_digest = semantic_sha256(audit)
    except (EchoEventStoreError, ValueError, TypeError, AttributeError) as exc:
        raise ScientificEchoWitnessError("science audit record failed semantic verification") from exc

    try:
        trusted_key = _expect_digest(expected_checkpoint_key_fingerprint_sha256, "checkpoint fingerprint")
        if not isinstance(checkpoint_bundles, list) or not checkpoint_bundles:
            raise ScientificEchoWitnessError("complete checkpoint chain required")
        verified_chain = verify_chain(checkpoint_bundles, trusted_key)
        verified = verify_bundle(checkpoint_bundles[-1], trusted_key)
    except (EchoCheckpointVerificationError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise ScientificEchoWitnessError("checkpoint chain authentication failed") from exc

    event_id = expected_payload["_outbox_event_id"]
    matching = [item for item in verified["events"] if item["event_id"] == event_id]
    if len(matching) != 1:
        raise ScientificEchoWitnessError("science event is not uniquely included in checkpoint")
    if matching[0]["semantic_sha256"] != semantic_digest:
        raise ScientificEchoWitnessError("signed checkpoint event digest mismatch")
    return {
        "schema": SCIENCE_WITNESS_SCHEMA,
        "status": "PASS",
        "claim_id": expected_claim_id,
        "run_id": receipt["run_id"],
        "event_id": event_id,
        "event_semantic_sha256": semantic_digest,
        "checkpoint_sha256": verified["checkpoint_sha256"],
        "checkpoint_sequence": verified["sequence"],
        "checkpoint_count": verified_chain["checkpoint_count"],
        "echo_signed_checkpoint_chain_verified": True,
        "checkpoint_key_fingerprint_sha256": verified["key_fingerprint_sha256"],
        "receipt_locally_reproduced": True,
        "echo_signed_event_inclusion_verified": True,
        "preexecution_freeze_verified": False,
        "prime_authorization_verified": False,
        "independent_process_attestation_verified": False,
        "third_party_witness_verified": False,
        "scientific_claim_proven": False,
        "claims_boundary": (
            "PASS establishes reproducibility of the narrow synthetic calculation "
            "and signed inclusion of its self-reported semantic event in a full "
            "predecessor-checked checkpoint chain under the caller-pinned ECHO key. "
            "It does NOT establish that PRIME "
            "authorized execution, independent pre-run freeze, third-party witness, "
            "trusted hardware, external retention, or scientific/physical validity."
        ),
    }

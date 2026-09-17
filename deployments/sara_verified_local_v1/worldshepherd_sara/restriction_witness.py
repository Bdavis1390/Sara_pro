from __future__ import annotations

from typing import Any

from .echo_checkpoint_verify import (
    EchoCheckpointVerificationError,
    verify_bundle,
)
from .echo_event_store import EchoEventStoreError, semantic_sha256
from .models import AuditRecord
from .restriction_observability import (
    RestrictionObservabilityError,
    project_restriction_audit_record,
)


RESTRICTION_WITNESS_SCHEMA = "WS-RESTRICTION-WITNESS-V1"


class RestrictionWitnessVerificationError(ValueError):
    pass


def verify_restriction_witness(
    record: dict[str, Any],
    checkpoint_bundle: dict[str, Any],
    *,
    expected_checkpoint_key_fingerprint_sha256: str,
) -> dict[str, Any]:
    """Verify one restriction event is included in a trusted signed ECHO checkpoint."""
    try:
        projected = project_restriction_audit_record(record)
    except RestrictionObservabilityError as exc:
        raise RestrictionWitnessVerificationError(
            f"restriction projection failed: {exc}"
        ) from exc

    try:
        audit = AuditRecord(**record)
        semantic_digest = semantic_sha256(audit)
    except (TypeError, ValueError, EchoEventStoreError) as exc:
        raise RestrictionWitnessVerificationError(
            "restriction semantic digest could not be reconstructed"
        ) from exc

    try:
        verified = verify_bundle(
            checkpoint_bundle,
            expected_checkpoint_key_fingerprint_sha256,
        )
    except EchoCheckpointVerificationError as exc:
        raise RestrictionWitnessVerificationError(
            f"checkpoint verification failed: {exc}"
        ) from exc

    event_id = projected["event_id"]
    matches = [
        item
        for item in verified["events"]
        if item["event_id"] == event_id
    ]
    if len(matches) != 1:
        raise RestrictionWitnessVerificationError(
            "restriction event is not uniquely witnessed by the checkpoint"
        )
    if matches[0]["semantic_sha256"] != semantic_digest:
        raise RestrictionWitnessVerificationError(
            "restriction semantic digest does not match the signed checkpoint"
        )

    return {
        "schema": RESTRICTION_WITNESS_SCHEMA,
        "status": "PASS",
        "restriction_id": projected["restriction_id"],
        "event_id": event_id,
        "authority": projected["authority"],
        "fingerprint_key_id": projected["fingerprint_key_id"],
        "checkpoint": {
            "checkpoint_id": verified["checkpoint_id"],
            "sequence": verified["sequence"],
            "checkpoint_sha256": verified["checkpoint_sha256"],
            "algorithm": "Ed25519",
            "key_id": verified["key_id"],
            "key_fingerprint_sha256": verified[
                "key_fingerprint_sha256"
            ],
        },
        "claims_boundary": (
            "PASS establishes that the exact bounded SARA restriction event is "
            "included in an Ed25519-signed ECHO checkpoint verified against the "
            "supplied trusted public-key fingerprint. It does not establish "
            "independent third-party witnessing, HSM/TPM custody, signer "
            "non-compromise, immutable external retention, policy correctness, "
            "customer/government acceptance, or independent reproduction."
        ),
    }

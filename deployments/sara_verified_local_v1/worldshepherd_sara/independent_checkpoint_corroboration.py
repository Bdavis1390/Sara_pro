from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .echo_checkpoint_verify import (
    EchoCheckpointVerificationError,
    verify_bundle,
)
from .overwatch_attestation_contract import OverwatchAttestationContract
from .overwatch_provenance import OverwatchProvenanceReceipt
from .overwatch_tripwire import (
    OverwatchDisposition,
    classify_overwatch_observation,
)


INDEPENDENT_CHECKPOINT_CORROBORATION_SCHEMA = (
    "WS-INDEPENDENT-CHECKPOINT-CORROBORATION-V1"
)
_CLAIMS_BOUNDARY = (
    "Cryptographic membership verification against the supplied signed local ECHO "
    "checkpoint only; monitor identity authentication, immutable/WORM retention, "
    "external anchoring, third-party attestation, privileged rollback resistance, "
    "authorization, FASA readiness, and execution are not established."
)


class IndependentCheckpointCorroborationError(ValueError):
    """Raised when supplied reviewer evidence cannot be corroborated safely."""


class IndependentCheckpointCorroboration(BaseModel):
    """Non-authorizing proof that OVERWATCH evidence is in a signed checkpoint."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-INDEPENDENT-CHECKPOINT-CORROBORATION-V1"] = (
        INDEPENDENT_CHECKPOINT_CORROBORATION_SCHEMA
    )
    observation_id: str = Field(min_length=1, max_length=160)
    monitor_id: str = Field(min_length=1, max_length=160)
    provenance_event_id: str = Field(min_length=1, max_length=200)
    decision_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    echo_semantic_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_sequence: int = Field(ge=1)
    checkpoint_id: str = Field(min_length=1, max_length=200)
    checkpoint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    checkpoint_key_id: str = Field(min_length=1, max_length=200)
    checkpoint_key_fingerprint_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_recomputed: Literal[True] = True
    checkpoint_signature_verified: Literal[True] = True
    checkpoint_membership_verified: Literal[True] = True
    monitor_verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    authorization_effect: Literal["NONE"] = "NONE"
    readiness_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False
    claims_boundary: str = _CLAIMS_BOUNDARY
    corroboration_digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def _canonical_payload(
    *,
    observation_id: str,
    monitor_id: str,
    provenance_event_id: str,
    decision_digest_sha256: str,
    echo_semantic_sha256: str,
    checkpoint_sequence: int,
    checkpoint_id: str,
    checkpoint_sha256: str,
    checkpoint_key_id: str,
    checkpoint_key_fingerprint_sha256: str,
) -> bytes:
    payload = {
        "schema": INDEPENDENT_CHECKPOINT_CORROBORATION_SCHEMA,
        "observation_id": observation_id,
        "monitor_id": monitor_id,
        "provenance_event_id": provenance_event_id,
        "decision_digest_sha256": decision_digest_sha256,
        "echo_semantic_sha256": echo_semantic_sha256,
        "checkpoint_sequence": checkpoint_sequence,
        "checkpoint_id": checkpoint_id,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_key_id": checkpoint_key_id,
        "checkpoint_key_fingerprint_sha256": checkpoint_key_fingerprint_sha256,
        "decision_recomputed": True,
        "checkpoint_signature_verified": True,
        "checkpoint_membership_verified": True,
        "monitor_verification_status": "UNVERIFIED",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def corroborate_overwatch_checkpoint(
    *,
    overwatch_attestation: OverwatchAttestationContract,
    overwatch_provenance: OverwatchProvenanceReceipt,
    checkpoint_bundle: Any,
    expected_checkpoint_key_fingerprint_sha256: str,
) -> IndependentCheckpointCorroboration:
    """Corroborate deterministic decision semantics and signed checkpoint membership.

    This function is read-only. It does not mutate SARA/ECHO state, authenticate
    the monitor, create PRIME approval, promote FASA readiness, or execute a side
    effect.
    """

    if overwatch_attestation.verification_status != "UNVERIFIED":
        raise IndependentCheckpointCorroborationError(
            "current OVERWATCH attestation must remain UNVERIFIED"
        )
    if overwatch_attestation.authorization_effect != "NONE":
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH attestation cannot confer authority"
        )
    if overwatch_attestation.execution_effect_applied is not False:
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH attestation cannot claim an execution side effect"
        )
    if overwatch_provenance.authorization_effect != "NONE":
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH provenance cannot confer authority"
        )
    if overwatch_provenance.execution_effect_applied is not False:
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH provenance cannot claim an execution side effect"
        )

    observation = overwatch_attestation.observation
    if overwatch_provenance.observation_id != observation.observation_id:
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH provenance observation binding mismatch"
        )

    recomputed = classify_overwatch_observation(observation)
    if recomputed.disposition == OverwatchDisposition.CONTINUE:
        raise IndependentCheckpointCorroborationError(
            "CONTINUE observation cannot support containment-intent provenance"
        )
    if recomputed.decision_digest_sha256 != overwatch_provenance.decision_digest_sha256:
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH provenance decision digest does not match deterministic recomputation"
        )

    try:
        verified = verify_bundle(
            checkpoint_bundle,
            expected_checkpoint_key_fingerprint_sha256,
        )
    except EchoCheckpointVerificationError as exc:
        raise IndependentCheckpointCorroborationError(
            "signed ECHO checkpoint verification failed"
        ) from exc

    membership = {
        item["event_id"]: item["semantic_sha256"]
        for item in verified["events"]
    }
    member_digest = membership.get(overwatch_provenance.provenance_event_id)
    if member_digest is None:
        raise IndependentCheckpointCorroborationError(
            "OVERWATCH provenance event is absent from the verified checkpoint"
        )
    if member_digest != overwatch_provenance.echo_semantic_sha256:
        raise IndependentCheckpointCorroborationError(
            "verified checkpoint semantic digest does not match OVERWATCH provenance receipt"
        )

    canonical = _canonical_payload(
        observation_id=observation.observation_id,
        monitor_id=observation.monitor_id,
        provenance_event_id=overwatch_provenance.provenance_event_id,
        decision_digest_sha256=overwatch_provenance.decision_digest_sha256,
        echo_semantic_sha256=overwatch_provenance.echo_semantic_sha256,
        checkpoint_sequence=verified["sequence"],
        checkpoint_id=verified["checkpoint_id"],
        checkpoint_sha256=verified["checkpoint_sha256"],
        checkpoint_key_id=verified["key_id"],
        checkpoint_key_fingerprint_sha256=verified["key_fingerprint_sha256"],
    )

    return IndependentCheckpointCorroboration(
        observation_id=observation.observation_id,
        monitor_id=observation.monitor_id,
        provenance_event_id=overwatch_provenance.provenance_event_id,
        decision_digest_sha256=overwatch_provenance.decision_digest_sha256,
        echo_semantic_sha256=overwatch_provenance.echo_semantic_sha256,
        checkpoint_sequence=verified["sequence"],
        checkpoint_id=verified["checkpoint_id"],
        checkpoint_sha256=verified["checkpoint_sha256"],
        checkpoint_key_id=verified["key_id"],
        checkpoint_key_fingerprint_sha256=verified["key_fingerprint_sha256"],
        corroboration_digest_sha256=hashlib.sha256(canonical).hexdigest(),
    )


def verify_independent_checkpoint_corroboration(
    corroboration: IndependentCheckpointCorroboration,
) -> None:
    """Raise if fixed non-authority invariants or digest-bound fields changed."""

    invariant_expectations = {
        "schema": INDEPENDENT_CHECKPOINT_CORROBORATION_SCHEMA,
        "decision_recomputed": True,
        "checkpoint_signature_verified": True,
        "checkpoint_membership_verified": True,
        "monitor_verification_status": "UNVERIFIED",
        "authorization_effect": "NONE",
        "readiness_effect": "NONE",
        "execution_effect_applied": False,
        "claims_boundary": _CLAIMS_BOUNDARY,
    }
    for field_name, expected_value in invariant_expectations.items():
        if getattr(corroboration, field_name) != expected_value:
            raise IndependentCheckpointCorroborationError(
                f"independent checkpoint corroboration invariant mismatch: {field_name}"
            )

    expected = hashlib.sha256(
        _canonical_payload(
            observation_id=corroboration.observation_id,
            monitor_id=corroboration.monitor_id,
            provenance_event_id=corroboration.provenance_event_id,
            decision_digest_sha256=corroboration.decision_digest_sha256,
            echo_semantic_sha256=corroboration.echo_semantic_sha256,
            checkpoint_sequence=corroboration.checkpoint_sequence,
            checkpoint_id=corroboration.checkpoint_id,
            checkpoint_sha256=corroboration.checkpoint_sha256,
            checkpoint_key_id=corroboration.checkpoint_key_id,
            checkpoint_key_fingerprint_sha256=(
                corroboration.checkpoint_key_fingerprint_sha256
            ),
        )
    ).hexdigest()
    if expected != corroboration.corroboration_digest_sha256:
        raise IndependentCheckpointCorroborationError(
            "independent checkpoint corroboration digest mismatch"
        )

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .registry_checkpoint import (
    REGISTRY_CHECKPOINT_META_KEY,
    RegistryCheckpointIntegrityError,
    parse_checkpoint_metadata,
)
from .registry_monotonic_witness import (
    REMOTE_WITNESS_MODE,
    RegistryMonotonicWitnessClient,
    RegistryMonotonicWitnessVerifier,
    RegistryWitnessUnavailable,
)
from .storage import DurableStore


class RegistryWitnessGateError(RegistryCheckpointIntegrityError):
    pass


class RegistryWitnessPreconditionStale(RegistryWitnessGateError):
    pass


@dataclass(frozen=True)
class RegistryWitnessPrecondition:
    """Immutable carrier for one prepared signed witness receipt.

    This object is not an authority artifact by itself. A consequential caller
    must re-verify ``witness_receipt_json`` with a pinned
    ``RegistryMonotonicWitnessVerifier`` and compare the signed coordinates to
    the current registry checkpoint while the registry transaction lock is held.
    """

    generation: int
    state_root_sha256: str
    commit_hash: str
    witness_id: str
    witness_mode: str
    witness_receipt_sha256: str
    witness_receipt_json: str

    def receipt(self) -> dict[str, Any]:
        try:
            value = json.loads(self.witness_receipt_json)
        except json.JSONDecodeError as exc:
            raise RegistryWitnessGateError(
                "registry witness precondition receipt is invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise RegistryWitnessGateError(
                "registry witness precondition receipt must be a JSON object"
            )
        return value

    def evidence(self) -> dict[str, Any]:
        return {
            "schema": "WS-SARA-REGISTRY-WITNESS-PRECONDITION-V2",
            "generation": self.generation,
            "state_root_sha256": self.state_root_sha256,
            "commit_hash": self.commit_hash,
            "witness_id": self.witness_id,
            "witness_mode": self.witness_mode,
            "witness_receipt_sha256": self.witness_receipt_sha256,
            "signed_receipt_embedded": True,
            "verification_required_at_use": True,
            "external_witnessed": False,
            "independence_verified": False,
            "claims_boundary": (
                "This precondition carries the signed receipt used during preparation. A consequential "
                "consumer must independently re-verify that receipt against its pinned witness trust "
                "root and compare the signed coordinates to the current registry checkpoint. Passing "
                "that cryptographic and coordinate check does not prove independent administration, "
                "external hosting, WORM retention, or post-transition checkpoint coverage."
            ),
        }


def _canonical_receipt_json(receipt: dict[str, Any]) -> str:
    return json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def prepare_registry_witness_precondition(
    store: DurableStore,
    client: RegistryMonotonicWitnessClient,
) -> RegistryWitnessPrecondition:
    """Fetch and verify a remote witness head outside the protected transaction.

    The full signed receipt is retained in the precondition so a consequential
    consumer can verify it again locally while holding the protected registry
    transaction lock. No network I/O is required during that second check.
    """

    local_status = store.checkpoint_status()
    try:
        head = client.transport.read_head(client.verifier.expected_namespace)
    except Exception as exc:
        raise RegistryWitnessUnavailable("unable to read registry witness head") from exc
    if head is None:
        raise RegistryWitnessUnavailable(
            "registry witness has no head for this namespace"
        )

    assessment = client.verifier.assess_local_checkpoint(local_status, head)
    if assessment.get("status") != "PASS":
        raise RegistryWitnessGateError(
            "current registry checkpoint is not covered by an exact signed witness head"
        )
    if assessment.get("signature_verified") is not True:
        raise RegistryWitnessGateError("registry witness signature was not verified")
    if assessment.get("monotonic_match") is not True:
        raise RegistryWitnessGateError(
            "registry witness does not exactly match local checkpoint"
        )
    if assessment.get("witness_mode") != REMOTE_WITNESS_MODE:
        raise RegistryWitnessGateError(
            "consequential registry witness precondition requires REMOTE_WITNESS mode"
        )

    verified_head = client.verifier.verify_receipt(head)
    return RegistryWitnessPrecondition(
        generation=int(assessment["generation"]),
        state_root_sha256=str(assessment["state_root_sha256"]),
        commit_hash=str(assessment["commit_hash"]),
        witness_id=str(assessment["witness_id"]),
        witness_mode=str(assessment["witness_mode"]),
        witness_receipt_sha256=str(assessment["witness_receipt_sha256"]),
        witness_receipt_json=_canonical_receipt_json(verified_head),
    )


def assert_registry_witness_precondition(
    registry: dict[str, Any],
    precondition: RegistryWitnessPrecondition,
    *,
    verifier: RegistryMonotonicWitnessVerifier,
) -> None:
    """Cryptographically and transactionally re-verify a prepared precondition."""

    if precondition.witness_mode != REMOTE_WITNESS_MODE:
        raise RegistryWitnessGateError(
            "consequential registry witness precondition must be REMOTE_WITNESS mode"
        )

    receipt = precondition.receipt()
    try:
        verified_receipt = verifier.verify_receipt(receipt)
    except Exception as exc:
        raise RegistryWitnessGateError(
            "registry witness precondition receipt failed pinned-key verification"
        ) from exc

    if verified_receipt.get("witness_mode") != REMOTE_WITNESS_MODE:
        raise RegistryWitnessGateError(
            "signed registry witness receipt is not REMOTE_WITNESS mode"
        )
    if verified_receipt.get("witness_id") != precondition.witness_id:
        raise RegistryWitnessGateError(
            "registry witness precondition witness identity mismatch"
        )
    if verified_receipt.get("receipt_sha256") != precondition.witness_receipt_sha256:
        raise RegistryWitnessGateError(
            "registry witness precondition receipt digest mismatch"
        )

    signed_coordinates = (
        int(verified_receipt.get("generation")),
        str(verified_receipt.get("state_root_sha256")),
        str(verified_receipt.get("commit_hash")),
    )
    prepared_coordinates = (
        precondition.generation,
        precondition.state_root_sha256,
        precondition.commit_hash,
    )
    if signed_coordinates != prepared_coordinates:
        raise RegistryWitnessGateError(
            "registry witness precondition fields do not match signed receipt"
        )

    metadata = parse_checkpoint_metadata(registry)
    if metadata is None:
        raise RegistryWitnessGateError(
            f"{REGISTRY_CHECKPOINT_META_KEY} is required for witness-gated action"
        )
    current_coordinates = (
        int(metadata["generation"]),
        str(metadata["state_root_sha256"]),
        str(metadata["commit_hash"]),
    )
    if current_coordinates != signed_coordinates:
        raise RegistryWitnessPreconditionStale(
            "registry changed after witness verification; obtain a fresh witness precondition"
        )

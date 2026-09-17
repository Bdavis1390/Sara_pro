from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registry_checkpoint import (
    REGISTRY_CHECKPOINT_META_KEY,
    RegistryCheckpointIntegrityError,
    parse_checkpoint_metadata,
)
from .registry_monotonic_witness import RegistryMonotonicWitnessClient
from .storage import DurableStore


class RegistryWitnessGateError(RegistryCheckpointIntegrityError):
    pass


class RegistryWitnessPreconditionStale(RegistryWitnessGateError):
    pass


@dataclass(frozen=True)
class RegistryWitnessPrecondition:
    generation: int
    state_root_sha256: str
    commit_hash: str
    witness_id: str
    witness_mode: str
    witness_receipt_sha256: str

    def evidence(self) -> dict[str, Any]:
        return {
            "schema": "WS-SARA-REGISTRY-WITNESS-PRECONDITION-V1",
            "generation": self.generation,
            "state_root_sha256": self.state_root_sha256,
            "commit_hash": self.commit_hash,
            "witness_id": self.witness_id,
            "witness_mode": self.witness_mode,
            "witness_receipt_sha256": self.witness_receipt_sha256,
            "signature_verified": True,
            "monotonic_match": True,
            "external_witnessed": False,
            "independence_verified": False,
            "claims_boundary": (
                "This precondition proves only that the exact local registry checkpoint matched a "
                "valid pinned-key monotonic witness receipt when the precondition was prepared. "
                "It does not prove independent administration, external hosting, WORM retention, "
                "or that a later post-transition checkpoint has been witnessed."
            ),
        }


def prepare_registry_witness_precondition(
    store: DurableStore,
    client: RegistryMonotonicWitnessClient,
) -> RegistryWitnessPrecondition:
    """Fetch and verify a witness head outside the protected registry transaction.

    The returned coordinates must be checked again inside the transaction. This
    avoids performing remote I/O while holding the registry lock without opening
    a time-of-check/time-of-use bypass: any intervening registry generation
    change makes the precondition stale and the transaction fails closed.
    """

    local_status = store.checkpoint_status()
    assessment = client.check(local_status, require_head=True)
    if assessment.get("status") != "PASS":
        raise RegistryWitnessGateError(
            "current registry checkpoint is not covered by an exact signed witness head"
        )
    if assessment.get("signature_verified") is not True:
        raise RegistryWitnessGateError("registry witness signature was not verified")
    if assessment.get("monotonic_match") is not True:
        raise RegistryWitnessGateError("registry witness does not exactly match local checkpoint")

    return RegistryWitnessPrecondition(
        generation=int(assessment["generation"]),
        state_root_sha256=str(assessment["state_root_sha256"]),
        commit_hash=str(assessment["commit_hash"]),
        witness_id=str(assessment["witness_id"]),
        witness_mode=str(assessment["witness_mode"]),
        witness_receipt_sha256=str(assessment["witness_receipt_sha256"]),
    )


def assert_registry_witness_precondition(
    registry: dict[str, Any],
    precondition: RegistryWitnessPrecondition,
) -> None:
    metadata = parse_checkpoint_metadata(registry)
    if metadata is None:
        raise RegistryWitnessGateError(
            f"{REGISTRY_CHECKPOINT_META_KEY} is required for witness-gated action"
        )
    actual = (
        int(metadata["generation"]),
        str(metadata["state_root_sha256"]),
        str(metadata["commit_hash"]),
    )
    expected = (
        precondition.generation,
        precondition.state_root_sha256,
        precondition.commit_hash,
    )
    if actual != expected:
        raise RegistryWitnessPreconditionStale(
            "registry changed after witness verification; obtain a fresh witness precondition"
        )

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .checkpoint_witness import (
    WitnessQuorumPolicy,
    WitnessReceipt,
    verify_checkpoint_quorum,
    verify_witness_quorum_policy,
)
from .snapshot_lineage import SnapshotCheckpoint


QUORUM_CERTIFICATE_SCHEMA = "WS-QUORUM-CERTIFICATE-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
Verifier = Callable[[bytes, bytes, str, str, str], bool]


class CheckpointQuorumCertificate(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[QUORUM_CERTIFICATE_SCHEMA] = QUORUM_CERTIFICATE_SCHEMA
    checkpoint: SnapshotCheckpoint
    policy: WitnessQuorumPolicy
    receipts: tuple[WitnessReceipt, ...]
    certificate_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sort_receipts(receipts: list[WitnessReceipt] | tuple[WitnessReceipt, ...]) -> tuple[WitnessReceipt, ...]:
    return tuple(
        sorted(
            receipts,
            key=lambda item: (item.witness_id, item.key_id, item.algorithm, item.receipt_digest),
        )
    )


def _payload_without_digest(certificate: CheckpointQuorumCertificate) -> dict[str, Any]:
    payload = certificate.model_dump(mode="json")
    payload.pop("certificate_digest", None)
    return payload


def build_checkpoint_quorum_certificate(
    *,
    checkpoint: SnapshotCheckpoint,
    policy: WitnessQuorumPolicy,
    receipts: list[WitnessReceipt],
    verifier: Verifier,
) -> CheckpointQuorumCertificate:
    ordered_receipts = _sort_receipts(receipts)
    if not verify_witness_quorum_policy(policy):
        raise ValueError("certificate requires a valid quorum policy")
    if not verify_checkpoint_quorum(
        checkpoint,
        receipts=list(ordered_receipts),
        policy=policy,
        verifier=verifier,
    ):
        raise ValueError("certificate requires a valid checkpoint quorum")

    payload: dict[str, Any] = {
        "schema": QUORUM_CERTIFICATE_SCHEMA,
        "checkpoint": checkpoint.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
        "receipts": [receipt.model_dump(mode="json") for receipt in ordered_receipts],
    }
    payload["certificate_digest"] = _digest(payload)
    return CheckpointQuorumCertificate.model_validate(payload)


def verify_checkpoint_quorum_certificate(
    certificate: CheckpointQuorumCertificate,
    *,
    verifier: Verifier,
) -> bool:
    if _digest(_payload_without_digest(certificate)) != certificate.certificate_digest:
        return False
    if certificate.receipts != _sort_receipts(certificate.receipts):
        return False
    if not verify_witness_quorum_policy(certificate.policy):
        return False
    return verify_checkpoint_quorum(
        certificate.checkpoint,
        receipts=list(certificate.receipts),
        policy=certificate.policy,
        verifier=verifier,
    )


def export_checkpoint_quorum_certificate(certificate: CheckpointQuorumCertificate) -> str:
    if _digest(_payload_without_digest(certificate)) != certificate.certificate_digest:
        raise ValueError("cannot export certificate with invalid digest")
    return json.dumps(
        certificate.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def import_checkpoint_quorum_certificate(
    payload: str,
    *,
    verifier: Verifier,
) -> CheckpointQuorumCertificate:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid certificate JSON") from exc

    certificate = CheckpointQuorumCertificate.model_validate(raw)
    if not verify_checkpoint_quorum_certificate(certificate, verifier=verifier):
        raise ValueError("certificate verification failed")
    return certificate

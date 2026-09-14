from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .snapshot_lineage import SnapshotCheckpoint


WITNESS_RECEIPT_SCHEMA = "WS-WITNESS-RECEIPT-V1"
WITNESS_QUORUM_POLICY_SCHEMA = "WS-WITNESS-QUORUM-POLICY-V1"
_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_ID_PATTERN = r"^[A-Za-z0-9._:-]+$"

Signer = Callable[[bytes], bytes]
Verifier = Callable[[bytes, bytes, str, str, str], bool]


class WitnessReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[WITNESS_RECEIPT_SCHEMA] = WITNESS_RECEIPT_SCHEMA
    witness_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN)
    key_id: str = Field(min_length=1, max_length=256)
    algorithm: str = Field(min_length=1, max_length=64)
    observed_utc: str = Field(min_length=1, max_length=64)
    checkpoint_digest: str = Field(pattern=_SHA256_PATTERN)
    signature_b64: str = Field(min_length=1)
    receipt_digest: str = Field(pattern=_SHA256_PATTERN)


class WitnessQuorumPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema: Literal[WITNESS_QUORUM_POLICY_SCHEMA] = WITNESS_QUORUM_POLICY_SCHEMA
    policy_id: str = Field(min_length=1, max_length=128, pattern=_ID_PATTERN)
    minimum_distinct_witnesses: int = Field(ge=1)
    allowed_witness_ids: tuple[str, ...]
    allowed_algorithms: tuple[str, ...]
    policy_digest: str = Field(pattern=_SHA256_PATTERN)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def _receipt_message_payload(
    *,
    witness_id: str,
    key_id: str,
    algorithm: str,
    observed_utc: str,
    checkpoint_digest: str,
) -> dict[str, Any]:
    return {
        "schema": WITNESS_RECEIPT_SCHEMA,
        "witness_id": witness_id,
        "key_id": key_id,
        "algorithm": algorithm,
        "observed_utc": observed_utc,
        "checkpoint_digest": checkpoint_digest,
    }


def _receipt_payload_without_digest(receipt: WitnessReceipt) -> dict[str, Any]:
    payload = receipt.model_dump(mode="json")
    payload.pop("receipt_digest", None)
    return payload


def _policy_payload_without_digest(policy: WitnessQuorumPolicy) -> dict[str, Any]:
    payload = policy.model_dump(mode="json")
    payload.pop("policy_digest", None)
    return payload


def build_witness_quorum_policy(
    *,
    policy_id: str,
    minimum_distinct_witnesses: int,
    allowed_witness_ids: list[str],
    allowed_algorithms: list[str],
) -> WitnessQuorumPolicy:
    witness_ids = tuple(sorted(set(allowed_witness_ids)))
    algorithms = tuple(sorted(set(allowed_algorithms)))
    if not witness_ids:
        raise ValueError("at least one allowed witness is required")
    if not algorithms:
        raise ValueError("at least one allowed algorithm is required")
    if minimum_distinct_witnesses > len(witness_ids):
        raise ValueError("quorum cannot exceed allowed witness count")

    payload: dict[str, Any] = {
        "schema": WITNESS_QUORUM_POLICY_SCHEMA,
        "policy_id": policy_id,
        "minimum_distinct_witnesses": minimum_distinct_witnesses,
        "allowed_witness_ids": witness_ids,
        "allowed_algorithms": algorithms,
    }
    payload["policy_digest"] = _digest(payload)
    return WitnessQuorumPolicy.model_validate(payload)


def verify_witness_quorum_policy(policy: WitnessQuorumPolicy) -> bool:
    if not policy.allowed_witness_ids or not policy.allowed_algorithms:
        return False
    if len(set(policy.allowed_witness_ids)) != len(policy.allowed_witness_ids):
        return False
    if len(set(policy.allowed_algorithms)) != len(policy.allowed_algorithms):
        return False
    if policy.minimum_distinct_witnesses > len(policy.allowed_witness_ids):
        return False
    return _digest(_policy_payload_without_digest(policy)) == policy.policy_digest


def create_witness_receipt(
    *,
    checkpoint: SnapshotCheckpoint,
    witness_id: str,
    key_id: str,
    algorithm: str,
    observed_utc: str,
    signer: Signer,
) -> WitnessReceipt:
    _parse_utc(observed_utc)
    message_payload = _receipt_message_payload(
        witness_id=witness_id,
        key_id=key_id,
        algorithm=algorithm,
        observed_utc=observed_utc,
        checkpoint_digest=checkpoint.checkpoint_digest,
    )
    signature = signer(_canonical_bytes(message_payload))
    if not isinstance(signature, bytes) or not signature:
        raise ValueError("signer must return non-empty bytes")

    payload = {
        **message_payload,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }
    payload["receipt_digest"] = _digest(payload)
    return WitnessReceipt.model_validate(payload)


def verify_witness_receipt(
    receipt: WitnessReceipt,
    *,
    checkpoint: SnapshotCheckpoint,
    policy: WitnessQuorumPolicy,
    verifier: Verifier,
) -> bool:
    if not verify_witness_quorum_policy(policy):
        return False
    try:
        _parse_utc(receipt.observed_utc)
    except (TypeError, ValueError):
        return False
    if _digest(_receipt_payload_without_digest(receipt)) != receipt.receipt_digest:
        return False
    if receipt.checkpoint_digest != checkpoint.checkpoint_digest:
        return False
    if receipt.witness_id not in policy.allowed_witness_ids:
        return False
    if receipt.algorithm not in policy.allowed_algorithms:
        return False

    try:
        signature = base64.b64decode(receipt.signature_b64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        return False
    if not signature:
        return False

    message_payload = _receipt_message_payload(
        witness_id=receipt.witness_id,
        key_id=receipt.key_id,
        algorithm=receipt.algorithm,
        observed_utc=receipt.observed_utc,
        checkpoint_digest=receipt.checkpoint_digest,
    )
    try:
        return bool(
            verifier(
                _canonical_bytes(message_payload),
                signature,
                receipt.algorithm,
                receipt.key_id,
                receipt.witness_id,
            )
        )
    except Exception:
        return False


def verify_checkpoint_quorum(
    checkpoint: SnapshotCheckpoint,
    *,
    receipts: list[WitnessReceipt],
    policy: WitnessQuorumPolicy,
    verifier: Verifier,
) -> bool:
    if not verify_witness_quorum_policy(policy):
        return False

    accepted_witnesses: set[str] = set()
    for receipt in receipts:
        if receipt.witness_id in accepted_witnesses:
            return False
        if not verify_witness_receipt(receipt, checkpoint=checkpoint, policy=policy, verifier=verifier):
            return False
        accepted_witnesses.add(receipt.witness_id)

    return len(accepted_witnesses) >= policy.minimum_distinct_witnesses

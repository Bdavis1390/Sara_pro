"""Witness-threshold envelopes for WS-CAE continuity checkpoints.

This module binds a linked continuity checkpoint to metadata about independent
witness receipts. It does not create or verify signatures, keys, tokens,
consensus messages, cryptocurrency transactions, or external transparency-log
receipts. Receipt cryptographic verification remains an external responsibility.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from .continuity_checkpoint import LinkedCheckpoint
from .continuity_validation import valid_content_id
from .continuity_witness import WitnessReceipt, assess_witnesses

SPEC = "WS-CAE-WITNESSED-CHECKPOINT-1"
VERIFICATION_BOUNDARY = "EXTERNAL_RECEIPT_CRYPTOGRAPHIC_VERIFICATION_REQUIRED"


def _receipt_key(receipt: WitnessReceipt) -> tuple:
    return (
        receipt.issuer.strip(),
        receipt.tree_size,
        receipt.root_hash,
        receipt.observed_at,
        receipt.verification_method.strip(),
        receipt.receipt_ref.strip(),
    )


def _canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _content_id(value: dict) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def build_witnessed_checkpoint(
    checkpoint: LinkedCheckpoint,
    receipts: tuple[WitnessReceipt, ...],
    *,
    threshold: int,
) -> dict:
    if checkpoint.tree_size < 0:
        raise ValueError("checkpoint tree_size must be non-negative")
    if not valid_content_id(checkpoint.root_hash):
        raise ValueError("checkpoint root must be a canonical lowercase SHA-256 content identifier")
    linked = checkpoint.previous_tree_size is not None or checkpoint.previous_root_hash is not None
    if linked and (checkpoint.previous_tree_size is None or checkpoint.previous_root_hash is None):
        raise ValueError("checkpoint predecessor metadata must be complete")
    if checkpoint.previous_tree_size is not None and checkpoint.previous_tree_size < 0:
        raise ValueError("previous_tree_size must be non-negative")
    if checkpoint.previous_root_hash is not None and not valid_content_id(checkpoint.previous_root_hash):
        raise ValueError("previous checkpoint root must be a canonical lowercase SHA-256 content identifier")

    assessment = assess_witnesses(
        receipts,
        expected_tree_size=checkpoint.tree_size,
        expected_root_hash=checkpoint.root_hash,
        threshold=threshold,
    )
    normalized_receipts = [asdict(item) for item in sorted(receipts, key=_receipt_key)]
    body = {
        "spec": SPEC,
        "checkpoint": checkpoint.to_dict(),
        "threshold": threshold,
        "receipt_count": len(receipts),
        "distinct_agreeing_witness_count": len(assessment.agreeing_issuers),
        "assessment_state": (
            "WITNESS_METADATA_THRESHOLD_SATISFIED"
            if assessment.passed
            else "WITNESS_METADATA_THRESHOLD_NOT_SATISFIED"
        ),
        "agreeing_issuers": list(assessment.agreeing_issuers),
        "rejected_receipts": list(assessment.rejected_receipts),
        "equivocation_issuers": list(assessment.equivocation_issuers),
        "receipt_verification_boundary": VERIFICATION_BOUNDARY,
        "receipts": normalized_receipts,
    }
    return {
        "content_id": _content_id(body),
        **body,
    }


def verify_witnessed_checkpoint(envelope: dict) -> bool:
    try:
        if envelope.get("spec") != SPEC:
            return False
        claimed_id = str(envelope["content_id"])
        if not valid_content_id(claimed_id):
            return False
        body = dict(envelope)
        del body["content_id"]
        if _content_id(body) != claimed_id:
            return False
        checkpoint_data = body["checkpoint"]
        checkpoint = LinkedCheckpoint(
            tree_size=int(checkpoint_data["tree_size"]),
            root_hash=str(checkpoint_data["root_hash"]),
            previous_tree_size=(
                None if checkpoint_data.get("previous_tree_size") is None
                else int(checkpoint_data["previous_tree_size"])
            ),
            previous_root_hash=(
                None if checkpoint_data.get("previous_root_hash") is None
                else str(checkpoint_data["previous_root_hash"])
            ),
        )
        receipts = tuple(
            WitnessReceipt(
                issuer=str(item["issuer"]),
                tree_size=int(item["tree_size"]),
                root_hash=str(item["root_hash"]),
                observed_at=str(item["observed_at"]),
                verification_method=str(item["verification_method"]),
                receipt_ref=str(item["receipt_ref"]),
            )
            for item in body["receipts"]
        )
        rebuilt = build_witnessed_checkpoint(
            checkpoint,
            receipts,
            threshold=int(body["threshold"]),
        )
        return rebuilt == envelope
    except (KeyError, TypeError, ValueError):
        return False

"""Portable verification bundles for WS-CAE continuity transparency.

The bundle binds a continuity content ID to an inclusion proof and checkpoint.
It performs no signing, consensus, networking, wallet, or asset operation.
"""

from __future__ import annotations

from dataclasses import asdict

from .continuity_checkpoint import LinkedCheckpoint
from .continuity_transparency import InclusionProof, verify_inclusion

SPEC = "WS-CAE-CONTINUITY-PROOF-BUNDLE-1"


def build_bundle(
    *,
    content_id: str,
    inclusion: InclusionProof,
    checkpoint: LinkedCheckpoint,
) -> dict:
    if inclusion.content_id != content_id:
        raise ValueError("inclusion proof content_id does not match bundle content_id")
    if inclusion.tree_size != checkpoint.tree_size:
        raise ValueError("inclusion proof tree size does not match checkpoint")
    if inclusion.root != checkpoint.root_hash:
        raise ValueError("inclusion proof root does not match checkpoint")
    if not verify_inclusion(inclusion):
        raise ValueError("inclusion proof does not verify")
    return {
        "spec": SPEC,
        "content_id": content_id,
        "inclusion_proof": asdict(inclusion),
        "checkpoint": checkpoint.to_dict(),
    }


def verify_bundle(bundle: dict) -> bool:
    try:
        if bundle.get("spec") != SPEC:
            return False
        proof_data = bundle["inclusion_proof"]
        checkpoint_data = bundle["checkpoint"]
        proof = InclusionProof(
            tree_size=int(proof_data["tree_size"]),
            leaf_index=int(proof_data["leaf_index"]),
            content_id=str(proof_data["content_id"]),
            root=str(proof_data["root"]),
            audit_path=tuple(str(item) for item in proof_data["audit_path"]),
        )
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
        return (
            str(bundle["content_id"]) == proof.content_id
            and proof.tree_size == checkpoint.tree_size
            and proof.root == checkpoint.root_hash
            and verify_inclusion(proof)
        )
    except (KeyError, TypeError, ValueError):
        return False

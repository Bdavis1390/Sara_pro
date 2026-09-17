"""Linked checkpoints for WS-CAE continuity transparency.

This layer makes append-only history explicit. It is metadata only and does not
provide consensus, networking, signing, or cryptocurrency operations.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from .continuity_transparency import root_hash


@dataclass(frozen=True)
class LinkedCheckpoint:
    tree_size: int
    root_hash: str
    previous_tree_size: int | None = None
    previous_root_hash: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def make_checkpoint(
    content_ids: tuple[str, ...],
    previous_content_ids: tuple[str, ...] | None = None,
) -> LinkedCheckpoint:
    if previous_content_ids is None:
        return LinkedCheckpoint(len(content_ids), root_hash(content_ids))
    if len(previous_content_ids) > len(content_ids):
        raise ValueError("previous tree cannot be larger than current tree")
    if content_ids[: len(previous_content_ids)] != previous_content_ids:
        raise ValueError("current tree does not extend previous tree as an exact prefix")
    return LinkedCheckpoint(
        tree_size=len(content_ids),
        root_hash=root_hash(content_ids),
        previous_tree_size=len(previous_content_ids),
        previous_root_hash=root_hash(previous_content_ids),
    )


def verify_extension(
    checkpoint: LinkedCheckpoint,
    current_content_ids: tuple[str, ...],
    previous_content_ids: tuple[str, ...] | None = None,
) -> bool:
    if checkpoint.tree_size != len(current_content_ids):
        return False
    if checkpoint.root_hash != root_hash(current_content_ids):
        return False
    if checkpoint.previous_tree_size is None and checkpoint.previous_root_hash is None:
        return previous_content_ids is None
    if checkpoint.previous_tree_size is None or checkpoint.previous_root_hash is None:
        return False
    if previous_content_ids is None:
        return False
    if checkpoint.previous_tree_size != len(previous_content_ids):
        return False
    if checkpoint.previous_root_hash != root_hash(previous_content_ids):
        return False
    return current_content_ids[: len(previous_content_ids)] == previous_content_ids

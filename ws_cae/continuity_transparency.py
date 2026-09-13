"""Append-only Merkle transparency primitives for WS-CAE continuity content IDs.

Metadata only. This module does not implement consensus, tokens, wallets, keys,
signing, transactions, networking, or asset movement.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(content_id: str) -> bytes:
    value = content_id.strip()
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("content_id must be sha256:<64 hex characters>")
    try:
        bytes.fromhex(value[7:])
    except ValueError as exc:
        raise ValueError("content_id digest must be hexadecimal") from exc
    return _sha256(b"\x00" + value.encode("ascii"))


def node_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise ValueError("Merkle node inputs must be 32-byte hashes")
    return _sha256(b"\x01" + left + right)


def _largest_power_of_two_less_than(n: int) -> int:
    if n < 2:
        raise ValueError("n must be at least 2")
    return 1 << ((n - 1).bit_length() - 1)


def tree_hash_from_leaf_hashes(leaves: tuple[bytes, ...]) -> bytes:
    n = len(leaves)
    if n == 0:
        return _sha256(b"")
    if n == 1:
        return leaves[0]
    k = _largest_power_of_two_less_than(n)
    return node_hash(
        tree_hash_from_leaf_hashes(leaves[:k]),
        tree_hash_from_leaf_hashes(leaves[k:]),
    )


def root_hash(content_ids: tuple[str, ...]) -> str:
    leaves = tuple(leaf_hash(value) for value in content_ids)
    return "sha256:" + tree_hash_from_leaf_hashes(leaves).hex()


@dataclass(frozen=True)
class InclusionProof:
    tree_size: int
    leaf_index: int
    content_id: str
    root: str
    audit_path: tuple[str, ...]


def _proof_path(leaves: tuple[bytes, ...], index: int) -> tuple[bytes, ...]:
    n = len(leaves)
    if n == 1:
        return tuple()
    k = _largest_power_of_two_less_than(n)
    if index < k:
        return _proof_path(leaves[:k], index) + (tree_hash_from_leaf_hashes(leaves[k:]),)
    return _proof_path(leaves[k:], index - k) + (tree_hash_from_leaf_hashes(leaves[:k]),)


def inclusion_proof(content_ids: tuple[str, ...], index: int) -> InclusionProof:
    if not content_ids:
        raise ValueError("cannot prove inclusion in an empty tree")
    if index < 0 or index >= len(content_ids):
        raise IndexError("leaf index is out of range")
    leaves = tuple(leaf_hash(value) for value in content_ids)
    path = _proof_path(leaves, index)
    return InclusionProof(
        tree_size=len(content_ids),
        leaf_index=index,
        content_id=content_ids[index],
        root=root_hash(content_ids),
        audit_path=tuple("sha256:" + item.hex() for item in path),
    )


def _rebuild(index: int, size: int, leaf: bytes, path: tuple[bytes, ...]) -> bytes:
    if size == 1:
        if path:
            raise ValueError("proof has extra nodes")
        return leaf
    if not path:
        raise ValueError("proof is incomplete")
    k = _largest_power_of_two_less_than(size)
    sibling = path[-1]
    rest = path[:-1]
    if index < k:
        return node_hash(_rebuild(index, k, leaf, rest), sibling)
    return node_hash(sibling, _rebuild(index - k, size - k, leaf, rest))


def verify_inclusion(proof: InclusionProof) -> bool:
    if proof.tree_size < 1 or proof.leaf_index < 0 or proof.leaf_index >= proof.tree_size:
        return False
    if not proof.root.startswith("sha256:"):
        return False
    try:
        path = tuple(bytes.fromhex(item[7:]) for item in proof.audit_path if item.startswith("sha256:"))
        if len(path) != len(proof.audit_path):
            return False
        rebuilt = _rebuild(proof.leaf_index, proof.tree_size, leaf_hash(proof.content_id), path)
        return proof.root == "sha256:" + rebuilt.hex()
    except (ValueError, IndexError):
        return False


def checkpoint(content_ids: tuple[str, ...]) -> dict:
    return {
        "spec": "WS-CAE-CONTINUITY-TRANSPARENCY-1",
        "tree_size": len(content_ids),
        "root_hash": root_hash(content_ids),
        "hash_algorithm": "SHA-256",
        "leaf_domain_separator": "00",
        "node_domain_separator": "01",
    }

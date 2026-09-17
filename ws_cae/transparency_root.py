"""Deterministic Merkle commitments for verified WS-CAE transparency statements.

This module commits to public statement payloads only. It does not sign,
register, broadcast, or modify cryptocurrency state.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from .scitt_statement import canonical_json

ROOT_SPEC = "WS-CAE-DATL-ROOT-1"


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def leaf_hash(statement: dict[str, Any]) -> bytes:
    return _h(b"\x00" + canonical_json(statement))


def node_hash(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


def _levels(leaves: list[bytes]) -> list[list[bytes]]:
    if not leaves:
        raise ValueError("at least one statement is required")
    levels = [leaves]
    current = leaves
    while len(current) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            nxt.append(node_hash(left, right))
        levels.append(nxt)
        current = nxt
    return levels


def inclusion_proof(leaves: list[bytes], index: int) -> list[dict[str, str]]:
    if index < 0 or index >= len(leaves):
        raise IndexError("leaf index out of range")
    levels = _levels(leaves)
    proof: list[dict[str, str]] = []
    position = index
    for level in levels[:-1]:
        sibling_index = position ^ 1
        if sibling_index >= len(level):
            sibling_index = position
        proof.append(
            {
                "side": "left" if sibling_index < position else "right",
                "sha256": level[sibling_index].hex(),
            }
        )
        position //= 2
    return proof


def verify_inclusion(statement: dict[str, Any], proof: list[dict[str, str]], root_hex: str) -> bool:
    current = leaf_hash(statement)
    for step in proof:
        sibling = bytes.fromhex(step["sha256"])
        side = step["side"]
        if side == "left":
            current = node_hash(sibling, current)
        elif side == "right":
            current = node_hash(current, sibling)
        else:
            return False
    return current.hex() == root_hex


def build_root(statements: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(statements)
    if not rows:
        raise ValueError("at least one statement is required")

    keyed: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for statement in rows:
        subject = statement.get("subject")
        if not isinstance(subject, dict) or not str(subject.get("id", "")).strip():
            raise ValueError("every statement requires subject.id")
        subject_id = str(subject["id"])
        if subject_id in seen:
            raise ValueError(f"duplicate subject.id: {subject_id}")
        seen.add(subject_id)
        keyed.append((subject_id, statement))

    keyed.sort(key=lambda item: item[0])
    ordered = [statement for _, statement in keyed]
    leaves = [leaf_hash(statement) for statement in ordered]
    levels = _levels(leaves)
    root_hex = levels[-1][0].hex()

    entries = []
    for index, (subject_id, statement) in enumerate(keyed):
        entries.append(
            {
                "subject_id": subject_id,
                "leaf_sha256": leaves[index].hex(),
                "proof": inclusion_proof(leaves, index),
            }
        )

    return {
        "spec": ROOT_SPEC,
        "hash_algorithm": "sha256",
        "tree_algorithm": "domain-separated-binary-merkle-v1",
        "statement_count": len(ordered),
        "root_sha256": root_hex,
        "entries": entries,
    }

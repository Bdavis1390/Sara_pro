"""Independent witness policy for continuity transparency checkpoints.

This module evaluates metadata about externally verifiable receipts. It does not
create signatures, keys, tokens, consensus messages, or cryptocurrency actions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WitnessReceipt:
    issuer: str
    tree_size: int
    root_hash: str
    observed_at: str
    verification_method: str
    receipt_ref: str


@dataclass(frozen=True)
class WitnessAssessment:
    passed: bool
    agreeing_issuers: tuple[str, ...]
    rejected_receipts: tuple[str, ...]
    equivocation_issuers: tuple[str, ...]


def detect_equivocation(receipts: tuple[WitnessReceipt, ...]) -> tuple[str, ...]:
    seen: dict[tuple[str, int], str] = {}
    conflicts: set[str] = set()
    for receipt in receipts:
        key = (receipt.issuer.strip(), receipt.tree_size)
        root = receipt.root_hash.strip()
        prior = seen.get(key)
        if prior is None:
            seen[key] = root
        elif prior != root:
            conflicts.add(key[0])
    return tuple(sorted(conflicts))


def assess_witnesses(
    receipts: tuple[WitnessReceipt, ...],
    *,
    expected_tree_size: int,
    expected_root_hash: str,
    threshold: int,
) -> WitnessAssessment:
    if threshold < 1:
        raise ValueError("threshold must be at least 1")
    equivocation = set(detect_equivocation(receipts))
    agreeing: set[str] = set()
    rejected: list[str] = []

    for receipt in receipts:
        issuer = receipt.issuer.strip()
        valid_shape = (
            bool(issuer)
            and receipt.tree_size >= 0
            and receipt.root_hash.startswith("sha256:")
            and bool(receipt.observed_at.strip())
            and bool(receipt.verification_method.strip())
            and bool(receipt.receipt_ref.strip())
        )
        if (
            not valid_shape
            or issuer in equivocation
            or receipt.tree_size != expected_tree_size
            or receipt.root_hash != expected_root_hash
        ):
            rejected.append(issuer or "<empty>")
            continue
        agreeing.add(issuer)

    agreeing_tuple = tuple(sorted(agreeing))
    return WitnessAssessment(
        passed=len(agreeing_tuple) >= threshold,
        agreeing_issuers=agreeing_tuple,
        rejected_receipts=tuple(rejected),
        equivocation_issuers=tuple(sorted(equivocation)),
    )

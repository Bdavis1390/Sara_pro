"""Worldshepherd Proof of Ownership lineage verifier.

The verifier checks technical PoO lineage integrity. It does not adjudicate legal
title or choose a winner when conflicting external claims exist.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

LINEAGE_SCHEMA = "WS-POO-LINEAGE-V1"
_ALLOWED_EVENT_TYPES = frozenset({"CLAIM", "TRANSFER", "RECOVERY"})


@dataclass(frozen=True)
class LineageNode:
    poo_digest: str
    asset_id: str
    claimant_id: str
    previous_poo_digest: Optional[str]
    event_type: str
    technical_poo_valid: bool
    superseded: bool = False
    revoked: bool = False


@dataclass(frozen=True)
class LineageDecision:
    schema: str
    status: str
    lineage_valid: bool
    fork_detected: bool
    cycle_detected: bool
    active_tip_digest: Optional[str]
    issues: List[str]
    digest: str
    legal_title_established: bool
    claims_boundary: Dict[str, bool]


def _canonical_nodes(nodes: Iterable[LineageNode]) -> list[dict[str, object]]:
    values = [asdict(node) for node in nodes]
    values.sort(key=lambda item: str(item["poo_digest"]))
    return values


def lineage_digest(nodes: Iterable[LineageNode]) -> str:
    raw = json.dumps(
        {"schema": LINEAGE_SCHEMA, "nodes": _canonical_nodes(nodes)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_lineage(nodes: Iterable[LineageNode]) -> LineageDecision:
    records = list(nodes)
    issues: list[str] = []

    if not records:
        issues.append("lineage is empty")
        return _decision(records, issues, fork=False, cycle=False, active_tip=None)

    digests = [node.poo_digest for node in records]
    if any(not digest for digest in digests):
        issues.append("PoO digest must be non-empty")
    if len(set(digests)) != len(digests):
        issues.append("duplicate PoO digest")

    asset_ids = {node.asset_id for node in records}
    if "" in asset_ids or len(asset_ids) != 1:
        issues.append("lineage must bind exactly one non-empty asset_id")

    invalid_types = sorted({node.event_type for node in records if node.event_type not in _ALLOWED_EVENT_TYPES})
    if invalid_types:
        issues.append("unsupported lineage event type")

    if any(not node.claimant_id for node in records):
        issues.append("claimant_id must be non-empty")
    if any(not node.technical_poo_valid for node in records):
        issues.append("lineage contains non-valid technical PoO")

    by_digest = {node.poo_digest: node for node in records if node.poo_digest}
    genesis = [node for node in records if node.previous_poo_digest is None]
    if len(genesis) != 1:
        issues.append("lineage must contain exactly one genesis PoO")
    elif genesis[0].event_type != "CLAIM":
        issues.append("genesis PoO must use CLAIM event type")

    children: dict[str, list[str]] = {}
    for node in records:
        parent = node.previous_poo_digest
        if parent is None:
            continue
        if parent not in by_digest:
            issues.append(f"missing prior PoO: {parent}")
            continue
        children.setdefault(parent, []).append(node.poo_digest)
        parent_node = by_digest[parent]
        if parent_node.revoked:
            issues.append(f"revoked PoO cannot have successor: {parent}")

    fork_detected = any(len(successors) > 1 for successors in children.values())
    if fork_detected:
        issues.append("forked ownership lineage detected")

    cycle_detected = _detect_cycle(by_digest)
    if cycle_detected:
        issues.append("cyclic ownership lineage detected")

    for node in records:
        has_child = bool(children.get(node.poo_digest))
        if has_child and not node.superseded:
            issues.append(f"prior PoO with successor must be superseded: {node.poo_digest}")
        if not has_child and node.superseded:
            issues.append(f"terminal PoO cannot be marked superseded: {node.poo_digest}")

    active_tips = [
        node
        for node in records
        if not children.get(node.poo_digest) and not node.revoked and not node.superseded
    ]
    active_tip = active_tips[0].poo_digest if len(active_tips) == 1 else None
    if len(active_tips) != 1:
        issues.append("lineage must have exactly one active technical tip")

    return _decision(
        records,
        issues,
        fork=fork_detected,
        cycle=cycle_detected,
        active_tip=active_tip,
    )


def _detect_cycle(by_digest: dict[str, LineageNode]) -> bool:
    for start in by_digest:
        seen: set[str] = set()
        current = start
        while current in by_digest:
            if current in seen:
                return True
            seen.add(current)
            parent = by_digest[current].previous_poo_digest
            if parent is None:
                break
            current = parent
    return False


def _decision(
    records: list[LineageNode],
    issues: list[str],
    *,
    fork: bool,
    cycle: bool,
    active_tip: Optional[str],
) -> LineageDecision:
    valid = not issues
    return LineageDecision(
        schema=LINEAGE_SCHEMA,
        status="LINEAGE_INTERNALLY_CONSISTENT" if valid else "LINEAGE_REVIEW_REQUIRED",
        lineage_valid=valid,
        fork_detected=fork,
        cycle_detected=cycle,
        active_tip_digest=active_tip if valid else None,
        issues=issues,
        digest=lineage_digest(records),
        legal_title_established=False,
        claims_boundary={
            "legal_title_adjudication": False,
            "government_registry_authority": False,
            "conflict_winner_selected": False,
            "transfer_execution": False,
            "live_value_movement": False,
        },
    )

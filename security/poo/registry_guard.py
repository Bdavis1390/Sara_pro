"""Multi-asset technical registry verifier for Worldshepherd Proof of Ownership.

This registry is an internal evidence/index layer. It groups immutable technical
ownership states by asset, verifies each lineage, and exposes exactly one active
technical tip per valid asset. It is not a government registry and does not
adjudicate legal title.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List

from security.poo.state_engine import TechnicalOwnershipState, evaluate_state_lineage, state_digest

REGISTRY_SCHEMA = "WS-POO-TECHNICAL-REGISTRY-V1"


@dataclass(frozen=True)
class RegistryDecision:
    schema: str
    status: str
    registry_valid: bool
    asset_count: int
    state_count: int
    active_poo_by_asset: Dict[str, str]
    active_claimant_by_asset: Dict[str, str]
    issues: List[str]
    digest: str
    legal_registry_authority: bool
    legal_title_established: bool
    claims_boundary: Dict[str, bool]


def registry_digest(states: Iterable[TechnicalOwnershipState]) -> str:
    canonical = [asdict(state) for state in states]
    canonical.sort(key=lambda item: (str(item["asset_id"]), int(item["generation"]), str(item["active_poo_digest"])))
    raw = json.dumps(
        {"schema": REGISTRY_SCHEMA, "states": canonical},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_registry(states: Iterable[TechnicalOwnershipState]) -> RegistryDecision:
    records = list(states)
    issues: list[str] = []
    active_poo: dict[str, str] = {}
    active_claimants: dict[str, str] = {}

    if not records:
        issues.append("technical ownership registry is empty")

    state_digests = [state_digest(state) for state in records]
    if len(set(state_digests)) != len(state_digests):
        issues.append("duplicate technical ownership state")

    poo_digests = [state.active_poo_digest for state in records]
    if len(set(poo_digests)) != len(poo_digests):
        issues.append("PoO digest reused across registry states")

    grouped: dict[str, list[TechnicalOwnershipState]] = {}
    for state in records:
        if not state.asset_id:
            issues.append("registry contains empty asset_id")
            continue
        grouped.setdefault(state.asset_id, []).append(state)

    for asset_id, asset_states in sorted(grouped.items()):
        lineage = evaluate_state_lineage(asset_states)
        if not lineage.lineage_valid:
            for issue in lineage.issues:
                issues.append(f"{asset_id}: {issue}")
            continue
        if not lineage.active_tip_digest:
            issues.append(f"{asset_id}: active technical tip unavailable")
            continue
        tip = next(
            (state for state in asset_states if state.active_poo_digest == lineage.active_tip_digest),
            None,
        )
        if tip is None:
            issues.append(f"{asset_id}: active technical tip not found in registry states")
            continue
        active_poo[asset_id] = tip.active_poo_digest
        active_claimants[asset_id] = tip.claimant_id

    valid = not issues
    return RegistryDecision(
        schema=REGISTRY_SCHEMA,
        status="TECHNICAL_REGISTRY_INTERNALLY_CONSISTENT" if valid else "TECHNICAL_REGISTRY_REVIEW_REQUIRED",
        registry_valid=valid,
        asset_count=len(grouped),
        state_count=len(records),
        active_poo_by_asset=active_poo if valid else {},
        active_claimant_by_asset=active_claimants if valid else {},
        issues=issues,
        digest=registry_digest(records),
        legal_registry_authority=False,
        legal_title_established=False,
        claims_boundary={
            "government_registry_authority": False,
            "legal_title_adjudication": False,
            "conflict_winner_selected": False,
            "transfer_execution": False,
            "live_value_movement": False,
            "external_validation_established": False,
        },
    )

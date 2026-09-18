"""Optimistic-concurrency commit guard for the Worldshepherd PoO technical registry.

The guard prepares a candidate registry mutation only. It never writes durable state,
changes legal title, moves value, rotates credentials, or executes a transfer.
Callers must persist an approved candidate through a separately governed SARA path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from security.poo.registry_guard import evaluate_registry, registry_digest
from security.poo.state_engine import (
    STATE_SCHEMA,
    StateTransitionDecision,
    TechnicalOwnershipState,
    state_digest,
)

COMMIT_SCHEMA = "WS-POO-REGISTRY-COMMIT-V1"


@dataclass(frozen=True)
class RegistryCommitDecision:
    schema: str
    operation: str
    status: str
    commit_ready: bool
    reasons: List[str]
    expected_registry_digest: str
    current_registry_digest: str
    candidate_registry_digest: Optional[str]
    candidate_state_digest: Optional[str]
    candidate_states: Optional[Tuple[TechnicalOwnershipState, ...]]
    technical_registry_committed: bool
    legal_title_changed: bool
    live_value_moved: bool
    external_transfer_executed: bool
    claims_boundary: Dict[str, bool]


def _boundary() -> Dict[str, bool]:
    return {
        "government_registry_authority": False,
        "legal_title_adjudication": False,
        "durable_registry_write_authority": False,
        "credential_rotation_authority": False,
        "live_value_movement": False,
        "external_transfer_execution": False,
        "external_validation_established": False,
    }


def prepare_registry_commit(
    current_states: Iterable[TechnicalOwnershipState],
    transition: StateTransitionDecision,
    *,
    expected_registry_digest: str,
) -> RegistryCommitDecision:
    """Prepare an atomic candidate mutation using compare-and-swap semantics."""
    current = list(current_states)
    reasons: list[str] = []
    current_digest = registry_digest(current)

    if not isinstance(expected_registry_digest, str) or not expected_registry_digest:
        reasons.append("expected registry digest must be non-empty")
    elif expected_registry_digest != current_digest:
        reasons.append("stale registry digest")

    if transition.schema != STATE_SCHEMA:
        reasons.append("unsupported transition schema")
    if not transition.ready or transition.candidate_state is None:
        reasons.append("state transition is not ready")
    if transition.technical_state_committed:
        reasons.append("transition already claims committed state")
    if transition.legal_title_changed or transition.live_value_moved or transition.external_transfer_executed:
        reasons.append("transition asserts forbidden external authority")

    candidate = transition.candidate_state
    candidate_states: Optional[Tuple[TechnicalOwnershipState, ...]] = None
    candidate_registry_digest: Optional[str] = None
    candidate_state_digest: Optional[str] = None

    if candidate is not None:
        if candidate.schema != STATE_SCHEMA:
            reasons.append("candidate uses unsupported technical-state schema")
        candidate_state_digest = state_digest(candidate)
        if any(state.active_poo_digest == candidate.active_poo_digest for state in current):
            reasons.append("candidate PoO already exists in registry")
        if any(state_digest(state) == candidate_state_digest for state in current):
            reasons.append("candidate technical state is a replay")

        same_asset = [state for state in current if state.asset_id == candidate.asset_id]
        if transition.operation == "BOOTSTRAP":
            if same_asset:
                reasons.append("bootstrap asset already exists in registry")
            if candidate.generation != 0:
                reasons.append("bootstrap candidate generation must be zero")
            if candidate.previous_poo_digest is not None or candidate.previous_coc_digest is not None:
                reasons.append("bootstrap candidate must have no predecessors")
        else:
            if not current:
                reasons.append("supersession requires an existing technical registry")
            current_decision = evaluate_registry(current) if current else None
            if current_decision is not None and not current_decision.registry_valid:
                reasons.append("current technical registry is not internally consistent")
            active_poo = (
                current_decision.active_poo_by_asset.get(candidate.asset_id)
                if current_decision is not None and current_decision.registry_valid
                else None
            )
            if active_poo is None:
                reasons.append("candidate asset has no active technical registry tip")
            elif candidate.previous_poo_digest != active_poo:
                reasons.append("candidate predecessor is not the active PoO tip")
            active_state = next(
                (state for state in same_asset if state.active_poo_digest == active_poo),
                None,
            )
            if active_state is not None:
                if candidate.previous_coc_digest != active_state.active_coc_digest:
                    reasons.append("candidate predecessor is not the active COC tip")
                if candidate.generation != active_state.generation + 1:
                    reasons.append("candidate generation does not advance active tip by one")

        if not reasons:
            proposed = tuple(current + [candidate])
            post = evaluate_registry(proposed)
            if not post.registry_valid:
                reasons.extend(f"post-commit registry: {issue}" for issue in post.issues)
            else:
                candidate_states = proposed
                candidate_registry_digest = post.digest

    ready = not reasons and candidate_states is not None
    return RegistryCommitDecision(
        schema=COMMIT_SCHEMA,
        operation=transition.operation,
        status="REGISTRY_COMMIT_CANDIDATE_READY" if ready else "REGISTRY_COMMIT_BLOCKED",
        commit_ready=ready,
        reasons=reasons,
        expected_registry_digest=expected_registry_digest,
        current_registry_digest=current_digest,
        candidate_registry_digest=candidate_registry_digest if ready else None,
        candidate_state_digest=candidate_state_digest,
        candidate_states=candidate_states if ready else None,
        technical_registry_committed=False,
        legal_title_changed=False,
        live_value_moved=False,
        external_transfer_executed=False,
        claims_boundary=_boundary(),
    )

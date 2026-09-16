"""Governed registry-commit readiness for Worldshepherd Proof of Ownership.

This is the final non-executing gate before a separately governed SARA persistence
workflow. It requires both a lineage-governed technical-state candidate and the
existing optimistic-concurrency registry commit guard. It never performs a durable
write, changes legal title, rotates credentials, moves value, or selects a winner.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

from security.poo.commit_guard import RegistryCommitDecision, prepare_registry_commit
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import TechnicalOwnershipState
from security.poo.state_governance_guard import GovernedStateTransitionDecision

REGISTRY_GOVERNANCE_SCHEMA = "WS-POO-REGISTRY-GOVERNANCE-V1"


@dataclass(frozen=True)
class GovernedRegistryCommitDecision:
    schema: str
    operation: str
    status: str
    ready: bool
    state_governance_ready: bool
    state_lineage_checked: bool
    state_lineage_valid: bool
    poo_lineage_valid: bool
    coc_lineage_valid: bool
    generation_valid: bool
    fork_detected: bool
    cycle_detected: bool
    active_tip_poo_digest: Optional[str]
    active_tip_state_digest: Optional[str]
    lineage_issue_count: int
    optimistic_concurrency_checked: bool
    optimistic_concurrency_match: bool
    expected_registry_digest: str
    current_registry_digest: str
    candidate_registry_digest: Optional[str]
    candidate_state_digest: Optional[str]
    reasons: List[str]
    commit_decision: Optional[RegistryCommitDecision]
    digest: str
    technical_registry_committed: bool
    durable_registry_write_authorized: bool
    conflict_winner_selected: bool
    lineage_auto_resolved: bool
    legal_title_changed: bool
    live_value_moved: bool
    external_transfer_executed: bool
    claims_boundary: Dict[str, bool]


def _boundary() -> Dict[str, bool]:
    return {
        "technical_registry_only": True,
        "government_registry_authority": False,
        "legal_title_adjudication": False,
        "durable_registry_write_authority": False,
        "credential_rotation_authority": False,
        "conflict_winner_selection": False,
        "automatic_lineage_resolution": False,
        "live_value_movement": False,
        "external_transfer_execution": False,
        "external_validation_established": False,
    }


def _digest(
    *,
    governed: GovernedStateTransitionDecision,
    expected_registry_digest: str,
    current_registry_digest: str,
    candidate_registry_digest: Optional[str],
) -> str:
    payload = {
        "schema": REGISTRY_GOVERNANCE_SCHEMA,
        "state_governance_digest": governed.digest,
        "expected_registry_digest": expected_registry_digest,
        "current_registry_digest": current_registry_digest,
        "candidate_registry_digest": candidate_registry_digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_governed_registry_commit(
    current_states: Iterable[TechnicalOwnershipState],
    governed: GovernedStateTransitionDecision,
    *,
    expected_registry_digest: str,
) -> GovernedRegistryCommitDecision:
    records = list(current_states)
    current_digest = registry_digest(records)
    concurrency_match = (
        isinstance(expected_registry_digest, str)
        and bool(expected_registry_digest)
        and expected_registry_digest == current_digest
    )
    reasons: list[str] = []
    commit: Optional[RegistryCommitDecision] = None

    if not governed.state_lineage_checked:
        reasons.append("state lineage was not checked")
    if not governed.state_lineage_valid:
        reasons.append("state lineage is not internally consistent")
    if not governed.ready or governed.transition is None:
        reasons.append("lineage-governed state transition is not ready")

    if governed.ready and governed.transition is not None:
        commit = prepare_registry_commit(
            records,
            governed.transition,
            expected_registry_digest=expected_registry_digest,
        )
        reasons.extend(commit.reasons)
    elif not concurrency_match:
        if not isinstance(expected_registry_digest, str) or not expected_registry_digest:
            reasons.append("expected registry digest must be non-empty")
        else:
            reasons.append("stale registry digest")

    ready = (
        not reasons
        and governed.ready
        and governed.state_lineage_valid
        and concurrency_match
        and commit is not None
        and commit.commit_ready
    )

    if not governed.state_lineage_valid:
        status = "REGISTRY_COMMIT_BLOCKED_STATE_LINEAGE"
    elif not concurrency_match:
        status = "REGISTRY_COMMIT_BLOCKED_STALE_SNAPSHOT"
    elif not governed.ready:
        status = "REGISTRY_COMMIT_BLOCKED_STATE_GOVERNANCE"
    elif ready:
        status = "REGISTRY_COMMIT_READY_WITH_FULL_GOVERNANCE"
    else:
        status = "REGISTRY_COMMIT_BLOCKED"

    candidate_registry_digest = (
        commit.candidate_registry_digest if commit is not None and commit.commit_ready else None
    )
    candidate_state_digest = (
        commit.candidate_state_digest if commit is not None else governed.candidate_state_digest
    )

    return GovernedRegistryCommitDecision(
        schema=REGISTRY_GOVERNANCE_SCHEMA,
        operation=governed.operation,
        status=status,
        ready=ready,
        state_governance_ready=governed.ready,
        state_lineage_checked=governed.state_lineage_checked,
        state_lineage_valid=governed.state_lineage_valid,
        poo_lineage_valid=governed.poo_lineage_valid,
        coc_lineage_valid=governed.coc_lineage_valid,
        generation_valid=governed.generation_valid,
        fork_detected=governed.fork_detected,
        cycle_detected=governed.cycle_detected,
        active_tip_poo_digest=governed.active_tip_poo_digest,
        active_tip_state_digest=governed.active_tip_state_digest,
        lineage_issue_count=governed.lineage_issue_count,
        optimistic_concurrency_checked=True,
        optimistic_concurrency_match=concurrency_match,
        expected_registry_digest=expected_registry_digest,
        current_registry_digest=current_digest,
        candidate_registry_digest=candidate_registry_digest,
        candidate_state_digest=candidate_state_digest,
        reasons=list(dict.fromkeys(reasons)),
        commit_decision=commit,
        digest=_digest(
            governed=governed,
            expected_registry_digest=expected_registry_digest,
            current_registry_digest=current_digest,
            candidate_registry_digest=candidate_registry_digest,
        ),
        technical_registry_committed=False,
        durable_registry_write_authorized=False,
        conflict_winner_selected=False,
        lineage_auto_resolved=False,
        legal_title_changed=False,
        live_value_moved=False,
        external_transfer_executed=False,
        claims_boundary=_boundary(),
    )

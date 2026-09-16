"""Governed genesis/bootstrap readiness for Worldshepherd Proof of Ownership.

Bootstrap is intentionally separate from ordinary lineage-governed supersession because
an empty technical registry has no active lineage tip. This guard permits exactly one
genesis candidate only when the current technical registry is empty, the PoO and exact
COC evidence produce a valid bootstrap state, and the optimistic-concurrency snapshot
matches the deterministic empty-registry digest. It never performs a durable write or
establishes legal title.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Dict, Iterable, List, Optional

from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.commit_guard import RegistryCommitDecision, prepare_registry_commit
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.registry_guard import registry_digest
from security.poo.state_engine import StateTransitionDecision, TechnicalOwnershipState, bootstrap_technical_state


BOOTSTRAP_GOVERNANCE_SCHEMA = "WS-POO-BOOTSTRAP-GOVERNANCE-V1"


@dataclass(frozen=True)
class GovernedBootstrapCommitDecision:
    schema: str
    status: str
    ready: bool
    empty_registry_verified: bool
    ownership_evidence_ready: bool
    coc_valid: bool
    state_transition_ready: bool
    optimistic_concurrency_checked: bool
    optimistic_concurrency_match: bool
    expected_registry_digest: str
    current_registry_digest: str
    candidate_registry_digest: Optional[str]
    candidate_state_digest: Optional[str]
    reasons: List[str]
    transition: StateTransitionDecision
    commit_decision: Optional[RegistryCommitDecision]
    digest: str
    technical_registry_committed: bool
    durable_registry_write_authorized: bool
    legal_title_changed: bool
    live_value_moved: bool
    credential_rotated: bool
    external_transfer_executed: bool
    claims_boundary: Dict[str, bool]


def _boundary() -> Dict[str, bool]:
    return {
        "technical_registry_bootstrap_only": True,
        "government_registry_authority": False,
        "legal_title_adjudication": False,
        "durable_registry_write_authority": False,
        "credential_rotation_authority": False,
        "live_value_movement": False,
        "external_transfer_execution": False,
        "external_validation_established": False,
    }


def _decision_digest(
    *,
    transition: StateTransitionDecision,
    expected_registry_digest: str,
    current_registry_digest: str,
    candidate_registry_digest: Optional[str],
    empty_registry_verified: bool,
) -> str:
    payload = {
        "schema": BOOTSTRAP_GOVERNANCE_SCHEMA,
        "transition": asdict(transition),
        "expected_registry_digest": expected_registry_digest,
        "current_registry_digest": current_registry_digest,
        "candidate_registry_digest": candidate_registry_digest,
        "empty_registry_verified": empty_registry_verified,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def evaluate_governed_bootstrap_commit(
    current_states: Iterable[TechnicalOwnershipState],
    ownership: OwnershipEvidence,
    coc: COCEvidence,
    *,
    expected_registry_digest: str,
) -> GovernedBootstrapCommitDecision:
    current = list(current_states)
    current_digest = registry_digest(current)
    empty = len(current) == 0
    concurrency_match = (
        isinstance(expected_registry_digest, str)
        and bool(expected_registry_digest)
        and expected_registry_digest == current_digest
    )
    ownership_decision = evaluate_ownership(ownership)
    coc_decision = evaluate_coc(coc)
    transition = bootstrap_technical_state(ownership, coc)
    reasons: list[str] = []

    if not empty:
        reasons.append("technical registry is not empty; bootstrap is permanently closed")
    if not concurrency_match:
        if not isinstance(expected_registry_digest, str) or not expected_registry_digest:
            reasons.append("expected registry digest must be non-empty")
        else:
            reasons.append("stale registry digest")
    if not ownership_decision.poo_valid:
        reasons.extend(ownership_decision.missing_predicates or ["genesis PoO evidence is not valid"])
    if not coc_decision.coc_valid:
        reasons.extend(coc_decision.missing_predicates or ["genesis COC evidence is not valid"])
    if not transition.ready or transition.candidate_state is None:
        reasons.extend(transition.reasons or ["bootstrap state transition is not ready"])

    commit: Optional[RegistryCommitDecision] = None
    if empty and concurrency_match and transition.ready and transition.candidate_state is not None:
        commit = prepare_registry_commit(
            current,
            transition,
            expected_registry_digest=expected_registry_digest,
        )
        reasons.extend(commit.reasons)

    ready = not reasons and commit is not None and commit.commit_ready
    if not empty:
        status = "REGISTRY_BOOTSTRAP_BLOCKED_NONEMPTY"
    elif not concurrency_match:
        status = "REGISTRY_BOOTSTRAP_BLOCKED_STALE_SNAPSHOT"
    elif not transition.ready:
        status = "REGISTRY_BOOTSTRAP_BLOCKED_EVIDENCE"
    elif ready:
        status = "REGISTRY_BOOTSTRAP_COMMIT_READY_WITH_FULL_GOVERNANCE"
    else:
        status = "REGISTRY_BOOTSTRAP_BLOCKED"

    candidate_registry_digest = (
        commit.candidate_registry_digest if commit is not None and commit.commit_ready else None
    )
    candidate_state_digest = (
        commit.candidate_state_digest if commit is not None else transition.candidate_state_digest
    )

    return GovernedBootstrapCommitDecision(
        schema=BOOTSTRAP_GOVERNANCE_SCHEMA,
        status=status,
        ready=ready,
        empty_registry_verified=empty,
        ownership_evidence_ready=ownership_decision.poo_valid,
        coc_valid=coc_decision.coc_valid,
        state_transition_ready=transition.ready,
        optimistic_concurrency_checked=True,
        optimistic_concurrency_match=concurrency_match,
        expected_registry_digest=expected_registry_digest,
        current_registry_digest=current_digest,
        candidate_registry_digest=candidate_registry_digest,
        candidate_state_digest=candidate_state_digest,
        reasons=list(dict.fromkeys(reasons)),
        transition=transition,
        commit_decision=commit,
        digest=_decision_digest(
            transition=transition,
            expected_registry_digest=expected_registry_digest,
            current_registry_digest=current_digest,
            candidate_registry_digest=candidate_registry_digest,
            empty_registry_verified=empty,
        ),
        technical_registry_committed=False,
        durable_registry_write_authorized=False,
        legal_title_changed=False,
        live_value_moved=False,
        credential_rotated=False,
        external_transfer_executed=False,
        claims_boundary=_boundary(),
    )

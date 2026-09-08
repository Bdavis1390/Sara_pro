from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .auth import Role, require_admin, resolve_role
from .models import AuditRecord
from .recursive_discovery import (
    initialize_state,
    make_seed,
    priority_score,
    run_recursive_cycle,
    state_digest,
)
from .recursive_discovery_api import OmegaCycleRequest, OmegaInitializeRequest
from .recursive_discovery_storage import OmegaStateStore


router = APIRouter(prefix="/admin/omega", tags=["WS-OMEGA"])


def _omega_store(request: Request) -> OmegaStateStore:
    return request.app.state.omega_store


@router.get("/status")
def omega_status(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    custody = _omega_store(request)
    storage_ok, storage_detail = custody.check_storage()
    return {
        "ok": storage_ok,
        "storage": storage_detail,
        "status": custody.status(),
    }


@router.get("/frontier")
def omega_frontier(
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
    limit: Annotated[int, Query(ge=1, le=128)] = 50,
    include_backlog: bool = False,
) -> dict[str, object]:
    require_admin(role)
    state = _omega_store(request).load()
    if state is None:
        return {
            "initialized": False,
            "cycle_index": 0,
            "state_digest": None,
            "nodes": [],
            "proposal_backlog_count": 0,
        }
    nodes = list(state.frontier)
    if include_backlog:
        nodes.extend(state.backlog)
    nodes = sorted(
        {node.node_id: node for node in nodes}.values(),
        key=lambda node: (-priority_score(node), node.depth, node.node_id),
    )[:limit]
    return {
        "initialized": True,
        "cycle_index": state.cycle_index,
        "state_digest": state_digest(state),
        "nodes": [
            {
                **node.model_dump(mode="json"),
                "priority_score": priority_score(node),
            }
            for node in nodes
        ],
        "proposal_backlog_count": len(state.proposal_backlog),
    }


@router.post("/init")
def omega_initialize(
    body: OmegaInitializeRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    seeds = [
        make_seed(
            kind=item.kind,
            domain=item.domain,
            statement=item.statement,
            source_refs=item.source_refs,
            confidence=item.confidence,
            evidence_state=item.evidence_state,
            cross_domain_tags=item.cross_domain_tags,
            falsification_tests=item.falsification_tests,
        )
        for item in body.seeds
    ]
    state = initialize_state(
        seeds,
        max_active_frontier=body.max_active_frontier,
    )
    try:
        state = _omega_store(request).initialize(state)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    digest = state_digest(state)
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="omega_initialized",
            actor=role.value,
            payload={
                "state_digest": digest,
                "seed_count": len(seeds),
                "frontier_count": len(state.frontier),
                "backlog_count": len(state.backlog),
                "claim_promotion_performed": False,
                "external_execution_performed": False,
            },
        )
    )
    return {
        "initialized": True,
        "state_digest": digest,
        "cycle_index": state.cycle_index,
        "frontier_count": len(state.frontier),
        "backlog_count": len(state.backlog),
        "claim_promotion_performed": False,
        "external_execution_performed": False,
    }


@router.post("/cycle")
def omega_cycle(
    body: OmegaCycleRequest,
    request: Request,
    role: Annotated[Role, Depends(resolve_role)],
) -> dict[str, object]:
    require_admin(role)
    custody = _omega_store(request)
    state = custody.load()
    if state is None:
        raise HTTPException(status_code=409, detail="WS-OMEGA state is not initialized")
    before = state_digest(state)
    next_state, report = run_recursive_cycle(
        state,
        body.proposals,
        policy=body.policy,
    )
    try:
        custody.replace(
            expected_state_digest=before,
            next_state=next_state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    request.app.state.store.append_audit(
        AuditRecord.create(
            event="omega_cycle_completed",
            actor=role.value,
            payload={
                "cycle_index": report.cycle_index,
                "state_before_digest": report.state_before_digest,
                "state_after_digest": report.state_after_digest,
                "report_digest": report.report_digest,
                "processed_parent_count": len(report.processed_parent_ids),
                "generated_node_count": len(report.generated_node_ids),
                "deferred_proposal_count": report.deferred_proposal_count,
                "stale_proposal_count": report.stale_proposal_count,
                "deepest_depth_seen": report.deepest_depth_seen,
                "claim_promotion_performed": False,
                "external_execution_performed": False,
            },
        )
    )
    return {
        "report": report.model_dump(mode="json"),
        "state_digest": report.state_after_digest,
    }

from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field, model_validator

from .qualification import canonical_digest


class DiscoveryKind(str, Enum):
    DOMAIN = "DOMAIN"
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    CONTRADICTION = "CONTRADICTION"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    EXPERIMENT = "EXPERIMENT"
    PARTNER = "PARTNER"
    OPPORTUNITY = "OPPORTUNITY"
    STANDARD = "STANDARD"
    PRIOR_ART = "PRIOR_ART"
    RISK = "RISK"


class DiscoveryEvidenceState(str, Enum):
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    CORROBORATED = "CORROBORATED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    SIMULATED = "SIMULATED"
    HYPOTHESIS = "HYPOTHESIS"
    SPECULATIVE = "SPECULATIVE"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


class DiscoveryNode(BaseModel):
    node_id: str = Field(pattern=r"^WS-OMEGA-[0-9a-f]{16}$")
    kind: DiscoveryKind
    domain: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    depth: int = Field(ge=0)
    parent_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_state: DiscoveryEvidenceState = DiscoveryEvidenceState.UNVERIFIED
    cross_domain_tags: list[str] = Field(default_factory=list)
    falsification_tests: list[str] = Field(default_factory=list)
    downstream_routes: list[str] = Field(default_factory=list)
    claim_promotion_allowed: bool = False
    physical_validation_claimed: bool = False
    external_execution_performed: bool = False

    @model_validator(mode="after")
    def fail_closed_claims_boundary(self) -> "DiscoveryNode":
        if self.claim_promotion_allowed:
            raise ValueError("recursive discovery cannot self-authorize claim promotion")
        if self.physical_validation_claimed:
            raise ValueError("recursive discovery cannot claim physical validation")
        if self.external_execution_performed:
            raise ValueError("recursive discovery cannot claim external execution")
        return self


class ExpansionProposal(BaseModel):
    parent_node_id: str = Field(pattern=r"^WS-OMEGA-[0-9a-f]{16}$")
    kind: DiscoveryKind
    domain: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_state: DiscoveryEvidenceState = DiscoveryEvidenceState.UNVERIFIED
    cross_domain_tags: list[str] = Field(default_factory=list)
    falsification_tests: list[str] = Field(default_factory=list)


class RecursiveDiscoveryPolicy(BaseModel):
    """Finite execution policy for an intentionally non-terminal search.

    Worldshepherd's "infinite" objective is represented by no global depth
    limit and by persistent frontier carry-forward. Each cycle remains bounded
    so runtime, auditability, and human governance stay enforceable.
    """

    parent_budget_per_cycle: int = Field(default=64, ge=1, le=10000)
    max_children_per_parent: int = Field(default=8, ge=1, le=1000)
    max_new_nodes_per_cycle: int = Field(default=256, ge=1, le=100000)
    max_active_frontier: int = Field(default=4096, ge=1, le=1000000)
    unbounded_global_depth: bool = True
    global_depth_limit: None = None
    preserve_negative_evidence: bool = True
    human_review_required_for_promotion: bool = True
    allow_claim_promotion: bool = False
    allow_external_execution: bool = False

    @model_validator(mode="after")
    def enforce_governance(self) -> "RecursiveDiscoveryPolicy":
        if not self.unbounded_global_depth:
            raise ValueError("WS-OMEGA requires unbounded_global_depth=true")
        if self.global_depth_limit is not None:
            raise ValueError("WS-OMEGA does not permit a terminal global depth")
        if not self.preserve_negative_evidence:
            raise ValueError("negative evidence must be preserved")
        if not self.human_review_required_for_promotion:
            raise ValueError("claim promotion requires human review")
        if self.allow_claim_promotion:
            raise ValueError("recursive engine may not self-authorize claim promotion")
        if self.allow_external_execution:
            raise ValueError("recursive engine may not self-authorize external execution")
        return self


class RecursiveDiscoveryState(BaseModel):
    schema: str = "ws-omega-state-1"
    cycle_index: int = Field(default=0, ge=0)
    frontier: list[DiscoveryNode] = Field(default_factory=list)
    backlog: list[DiscoveryNode] = Field(default_factory=list)
    explored_node_ids: list[str] = Field(default_factory=list)
    prior_state_digest: str | None = None


class RecursiveCycleReport(BaseModel):
    schema: str = "ws-omega-cycle-report-1"
    cycle_index: int
    state_before_digest: str
    state_after_digest: str
    processed_parent_ids: list[str]
    generated_node_ids: list[str]
    duplicate_node_ids: list[str]
    deferred_proposal_count: int
    active_frontier_count: int
    backlog_count: int
    deepest_depth_seen: int
    global_depth_limit: None = None
    physical_infinity_claimed: bool = False
    claim_promotion_performed: bool = False
    external_execution_performed: bool = False
    report_digest: str = ""


def _semantic_material(
    *,
    kind: DiscoveryKind,
    domain: str,
    statement: str,
    parent_ids: list[str],
    source_refs: list[str],
) -> dict[str, object]:
    return {
        "kind": kind.value,
        "domain": domain.strip(),
        "statement": statement.strip(),
        "parent_ids": sorted(set(parent_ids)),
        "source_refs": sorted(set(source_refs)),
    }


def _node_id(material: dict[str, object]) -> str:
    return "WS-OMEGA-" + canonical_digest(material).split(":", 1)[1][:16]


def route_node(kind: DiscoveryKind) -> list[str]:
    routes = {
        DiscoveryKind.DOMAIN: ["ECHO", "SARA-ADE", "SARA-COVERAGE"],
        DiscoveryKind.OBSERVATION: ["ECHO", "SARA-ADE", "PVK"],
        DiscoveryKind.HYPOTHESIS: ["SARA-ADE", "PVK", "RED-TEAM", "PRIME"],
        DiscoveryKind.CONTRADICTION: ["SARA-CONTRADICTION", "PVK", "RED-TEAM", "PRIME"],
        DiscoveryKind.NEGATIVE_SPACE: ["SARA-ADE", "SARA-CONTRADICTION", "PVK"],
        DiscoveryKind.EXPERIMENT: ["SARA-ADE", "PVK", "ECHO", "PRIME"],
        DiscoveryKind.PARTNER: ["PARTNER-SCREENING", "PRE", "ECHO"],
        DiscoveryKind.OPPORTUNITY: ["PRE", "PARTNER-SCREENING", "ECHO"],
        DiscoveryKind.STANDARD: ["PRE", "ECHO", "PRIME-TEVV"],
        DiscoveryKind.PRIOR_ART: ["PRE", "SARA-CONTRADICTION", "PRIME"],
        DiscoveryKind.RISK: ["PRIME", "OVERWATCH", "RED-TEAM"],
    }
    return list(routes[kind])


def make_seed(
    *,
    kind: DiscoveryKind,
    domain: str,
    statement: str,
    source_refs: Iterable[str] = (),
    confidence: float = 0.0,
    evidence_state: DiscoveryEvidenceState = DiscoveryEvidenceState.UNVERIFIED,
    cross_domain_tags: Iterable[str] = (),
    falsification_tests: Iterable[str] = (),
) -> DiscoveryNode:
    refs = sorted(set(source_refs))
    material = _semantic_material(
        kind=kind,
        domain=domain,
        statement=statement,
        parent_ids=[],
        source_refs=refs,
    )
    return DiscoveryNode(
        node_id=_node_id(material),
        kind=kind,
        domain=domain.strip(),
        statement=statement.strip(),
        depth=0,
        parent_ids=[],
        source_refs=refs,
        confidence=confidence,
        evidence_state=evidence_state,
        cross_domain_tags=sorted(set(cross_domain_tags)),
        falsification_tests=list(falsification_tests),
        downstream_routes=route_node(kind),
    )


def make_child(parent: DiscoveryNode, proposal: ExpansionProposal) -> DiscoveryNode:
    material = _semantic_material(
        kind=proposal.kind,
        domain=proposal.domain,
        statement=proposal.statement,
        parent_ids=[parent.node_id],
        source_refs=proposal.source_refs,
    )
    return DiscoveryNode(
        node_id=_node_id(material),
        kind=proposal.kind,
        domain=proposal.domain.strip(),
        statement=proposal.statement.strip(),
        depth=parent.depth + 1,
        parent_ids=[parent.node_id],
        source_refs=sorted(set(proposal.source_refs)),
        confidence=proposal.confidence,
        evidence_state=proposal.evidence_state,
        cross_domain_tags=sorted(set(proposal.cross_domain_tags)),
        falsification_tests=list(proposal.falsification_tests),
        downstream_routes=route_node(proposal.kind),
    )


def priority_score(node: DiscoveryNode) -> float:
    falsifiability = min(len(node.falsification_tests), 3) / 3.0
    cross_domain = min(len(node.cross_domain_tags), 4) / 4.0
    evidence_bonus = {
        DiscoveryEvidenceState.SOURCE_VERIFIED: 1.0,
        DiscoveryEvidenceState.CORROBORATED: 0.9,
        DiscoveryEvidenceState.SINGLE_SOURCE: 0.65,
        DiscoveryEvidenceState.SIMULATED: 0.55,
        DiscoveryEvidenceState.HYPOTHESIS: 0.35,
        DiscoveryEvidenceState.CONFLICTING: 0.3,
        DiscoveryEvidenceState.SPECULATIVE: 0.15,
        DiscoveryEvidenceState.UNVERIFIED: 0.1,
    }[node.evidence_state]
    kind_bonus = {
        DiscoveryKind.CONTRADICTION: 1.0,
        DiscoveryKind.NEGATIVE_SPACE: 0.95,
        DiscoveryKind.EXPERIMENT: 0.9,
        DiscoveryKind.OPPORTUNITY: 0.85,
        DiscoveryKind.PRIOR_ART: 0.85,
        DiscoveryKind.OBSERVATION: 0.8,
        DiscoveryKind.RISK: 0.8,
        DiscoveryKind.HYPOTHESIS: 0.7,
        DiscoveryKind.STANDARD: 0.7,
        DiscoveryKind.PARTNER: 0.65,
        DiscoveryKind.DOMAIN: 0.5,
    }[node.kind]
    return round(
        0.35 * node.confidence
        + 0.25 * evidence_bonus
        + 0.20 * falsifiability
        + 0.10 * cross_domain
        + 0.10 * kind_bonus,
        12,
    )


def state_digest(state: RecursiveDiscoveryState) -> str:
    return canonical_digest(state.model_dump(mode="json"))


def _sort_nodes(nodes: Iterable[DiscoveryNode]) -> list[DiscoveryNode]:
    return sorted(
        nodes,
        key=lambda node: (-priority_score(node), node.depth, node.node_id),
    )


def initialize_state(seeds: Iterable[DiscoveryNode], *, max_active_frontier: int = 4096) -> RecursiveDiscoveryState:
    unique = {seed.node_id: seed for seed in seeds}
    ranked = _sort_nodes(unique.values())
    return RecursiveDiscoveryState(
        frontier=ranked[:max_active_frontier],
        backlog=ranked[max_active_frontier:],
    )


def run_recursive_cycle(
    state: RecursiveDiscoveryState,
    proposals: Iterable[ExpansionProposal],
    *,
    policy: RecursiveDiscoveryPolicy | None = None,
) -> tuple[RecursiveDiscoveryState, RecursiveCycleReport]:
    active_policy = policy or RecursiveDiscoveryPolicy()
    before_digest = state_digest(state)

    ranked_frontier = _sort_nodes(state.frontier)
    processed = ranked_frontier[: active_policy.parent_budget_per_cycle]
    unprocessed = ranked_frontier[active_policy.parent_budget_per_cycle :]
    processed_ids = {node.node_id for node in processed}
    known_ids = {
        node.node_id
        for node in [*state.frontier, *state.backlog]
    } | set(state.explored_node_ids)

    grouped: dict[str, list[ExpansionProposal]] = {}
    deferred = 0
    for proposal in proposals:
        if proposal.parent_node_id not in processed_ids:
            deferred += 1
            continue
        grouped.setdefault(proposal.parent_node_id, []).append(proposal)

    parent_by_id = {node.node_id: node for node in processed}
    generated: list[DiscoveryNode] = []
    duplicates: list[str] = []
    new_budget = active_policy.max_new_nodes_per_cycle

    for parent in processed:
        candidates = grouped.get(parent.node_id, [])[: active_policy.max_children_per_parent]
        for proposal in candidates:
            if new_budget <= 0:
                deferred += 1
                continue
            child = make_child(parent, proposal)
            if child.node_id in known_ids:
                duplicates.append(child.node_id)
                continue
            known_ids.add(child.node_id)
            generated.append(child)
            new_budget -= 1

    candidate_active = _sort_nodes([*unprocessed, *generated])
    carry_backlog = _sort_nodes(state.backlog)
    active = candidate_active[: active_policy.max_active_frontier]
    overflow = candidate_active[active_policy.max_active_frontier :]

    if len(active) < active_policy.max_active_frontier and carry_backlog:
        room = active_policy.max_active_frontier - len(active)
        active = _sort_nodes([*active, *carry_backlog[:room]])
        carry_backlog = carry_backlog[room:]

    backlog = _sort_nodes([*carry_backlog, *overflow])
    explored = list(dict.fromkeys([*state.explored_node_ids, *[node.node_id for node in processed]]))

    next_state = RecursiveDiscoveryState(
        cycle_index=state.cycle_index + 1,
        frontier=active,
        backlog=backlog,
        explored_node_ids=explored,
        prior_state_digest=before_digest,
    )
    after_digest = state_digest(next_state)
    all_depths = [node.depth for node in [*next_state.frontier, *next_state.backlog, *processed]]
    deepest = max(all_depths, default=0)

    report_payload = {
        "schema": "ws-omega-cycle-report-1",
        "cycle_index": next_state.cycle_index,
        "state_before_digest": before_digest,
        "state_after_digest": after_digest,
        "processed_parent_ids": [node.node_id for node in processed],
        "generated_node_ids": [node.node_id for node in generated],
        "duplicate_node_ids": sorted(set(duplicates)),
        "deferred_proposal_count": deferred,
        "active_frontier_count": len(next_state.frontier),
        "backlog_count": len(next_state.backlog),
        "deepest_depth_seen": deepest,
        "global_depth_limit": None,
        "physical_infinity_claimed": False,
        "claim_promotion_performed": False,
        "external_execution_performed": False,
    }
    report = RecursiveCycleReport(
        **report_payload,
        report_digest=canonical_digest(report_payload),
    )
    return next_state, report


def verify_cycle_report(report: RecursiveCycleReport) -> bool:
    payload = report.model_dump(mode="json")
    expected = payload.pop("report_digest")
    return expected == canonical_digest(payload)

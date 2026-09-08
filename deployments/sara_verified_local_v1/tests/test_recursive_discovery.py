import pytest

from worldshepherd_sara.recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    DiscoveryNode,
    ExpansionProposal,
    RecursiveDiscoveryPolicy,
    initialize_state,
    make_seed,
    run_recursive_cycle,
    state_digest,
    verify_cycle_report,
)


def _proposal(parent_id: str, statement: str, *, kind: DiscoveryKind = DiscoveryKind.HYPOTHESIS):
    return ExpansionProposal(
        parent_node_id=parent_id,
        kind=kind,
        domain="cross-domain discovery",
        statement=statement,
        confidence=0.6,
        evidence_state=DiscoveryEvidenceState.HYPOTHESIS,
        cross_domain_tags=["physics", "materials"],
        falsification_tests=["attempt cheapest disconfirming benchmark"],
    )


def test_seed_routes_into_existing_worldshepherd_controls():
    seed = make_seed(
        kind=DiscoveryKind.OPPORTUNITY,
        domain="strong-field QED",
        statement="A facility call may support a bounded validation campaign.",
        confidence=0.8,
        evidence_state=DiscoveryEvidenceState.SINGLE_SOURCE,
    )
    assert seed.depth == 0
    assert seed.claim_promotion_allowed is False
    assert seed.physical_validation_claimed is False
    assert seed.external_execution_performed is False
    assert "PRE" in seed.downstream_routes
    assert "PARTNER-SCREENING" in seed.downstream_routes
    assert "ECHO" in seed.downstream_routes


def test_one_cycle_is_bounded_but_global_depth_is_not():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="quantum vacuum",
        statement="Explore validated and falsifiable adjacent observations.",
    )
    state = initialize_state([seed])
    policy = RecursiveDiscoveryPolicy(parent_budget_per_cycle=1, max_children_per_parent=1)
    next_state, report = run_recursive_cycle(
        state,
        [_proposal(seed.node_id, "Test a polarization-systematics hypothesis.")],
        policy=policy,
    )
    assert next_state.cycle_index == 1
    assert len(report.processed_parent_ids) == 1
    assert len(report.generated_node_ids) == 1
    assert next_state.frontier[0].depth == 1
    assert report.global_depth_limit is None
    assert report.physical_infinity_claimed is False
    assert report.claim_promotion_performed is False
    assert report.external_execution_performed is False


def test_recursion_can_continue_past_arbitrary_prior_depths():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="recursive validation",
        statement="Seed an intentionally non-terminal governed search.",
    )
    state = initialize_state([seed])
    policy = RecursiveDiscoveryPolicy(parent_budget_per_cycle=1, max_children_per_parent=1)

    for index in range(25):
        parent = state.frontier[0]
        state, report = run_recursive_cycle(
            state,
            [_proposal(parent.node_id, f"Recursive falsifiable child {index}.")],
            policy=policy,
        )

    assert state.cycle_index == 25
    assert state.frontier[0].depth == 25
    assert report.deepest_depth_seen == 25
    assert report.global_depth_limit is None


def test_frontier_overflow_is_preserved_in_backlog():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="broad search",
        statement="Generate multiple adjacent discovery branches.",
    )
    state = initialize_state([seed], max_active_frontier=1)
    policy = RecursiveDiscoveryPolicy(
        parent_budget_per_cycle=1,
        max_children_per_parent=3,
        max_new_nodes_per_cycle=3,
        max_active_frontier=1,
    )
    proposals = [
        _proposal(seed.node_id, "Branch A"),
        _proposal(seed.node_id, "Branch B", kind=DiscoveryKind.CONTRADICTION),
        _proposal(seed.node_id, "Branch C", kind=DiscoveryKind.NEGATIVE_SPACE),
    ]
    next_state, report = run_recursive_cycle(state, proposals, policy=policy)
    assert len(next_state.frontier) == 1
    assert len(next_state.backlog) == 2
    assert report.active_frontier_count == 1
    assert report.backlog_count == 2
    assert len({node.node_id for node in [*next_state.frontier, *next_state.backlog]}) == 3


def test_duplicate_proposals_are_deduplicated_before_expansion():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="dedupe",
        statement="Dedupe equivalent expansions.",
    )
    state = initialize_state([seed])
    proposal = _proposal(seed.node_id, "Same semantic child")
    next_state, report = run_recursive_cycle(state, [proposal, proposal])
    assert len(next_state.frontier) == 1
    assert len(report.generated_node_ids) == 1
    assert report.deferred_proposal_count == 0


def test_deferred_proposals_and_parent_survive_cycle_budget():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="proposal continuity",
        statement="Keep work that exceeds one-cycle resource limits.",
    )
    state = initialize_state([seed])
    policy = RecursiveDiscoveryPolicy(
        parent_budget_per_cycle=1,
        max_children_per_parent=1,
        max_new_nodes_per_cycle=1,
    )
    proposals = [
        _proposal(seed.node_id, "Deferred A"),
        _proposal(seed.node_id, "Deferred B"),
        _proposal(seed.node_id, "Deferred C"),
    ]
    next_state, report = run_recursive_cycle(state, proposals, policy=policy)
    all_nodes = [*next_state.frontier, *next_state.backlog]
    assert any(node.node_id == seed.node_id for node in all_nodes)
    assert len(next_state.proposal_backlog) == 2
    assert report.deferred_proposal_count == 2
    assert report.proposal_backlog_count == 2


def test_backlog_nodes_can_reenter_active_frontier_by_priority():
    low = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="low",
        statement="Low-priority active seed.",
    )
    high = make_seed(
        kind=DiscoveryKind.CONTRADICTION,
        domain="high",
        statement="High-priority contradiction seed.",
        confidence=1.0,
        evidence_state=DiscoveryEvidenceState.SOURCE_VERIFIED,
        falsification_tests=["reproduce contradiction"],
    )
    state = initialize_state([low, high], max_active_frontier=1)
    assert state.frontier[0].node_id == high.node_id
    # Force the lower-priority node into the active slot and the high-priority node into backlog,
    # then prove the global rerank removes backlog starvation while preserving the same one-slot budget.
    state = state.model_copy(update={"frontier": [low], "backlog": [high]})
    policy = RecursiveDiscoveryPolicy(max_active_frontier=1)
    next_state, _ = run_recursive_cycle(state, [], policy=policy)
    assert next_state.frontier[0].node_id == high.node_id
    assert next_state.backlog[0].node_id == low.node_id


def test_nodes_without_proposals_are_not_silently_marked_explored():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="idle frontier",
        statement="Remain pending until expansion evidence arrives.",
    )
    state = initialize_state([seed])
    next_state, report = run_recursive_cycle(state, [])
    assert next_state.frontier[0].node_id == seed.node_id
    assert seed.node_id not in next_state.explored_node_ids
    assert report.processed_parent_ids == []


def test_stale_proposals_are_reported_not_executed():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="stale proposals",
        statement="Detect proposals that no longer reference a live frontier node.",
    )
    state = initialize_state([seed])
    state, _ = run_recursive_cycle(state, [_proposal(seed.node_id, "First child")])
    _, report = run_recursive_cycle(state, [_proposal(seed.node_id, "Late stale child")])
    assert report.stale_proposal_count == 1
    assert report.generated_node_ids == []


def test_claims_and_external_execution_fail_closed():
    with pytest.raises(ValueError, match="claim promotion"):
        DiscoveryNode(
            node_id="WS-OMEGA-0123456789abcdef",
            kind=DiscoveryKind.HYPOTHESIS,
            domain="unsafe promotion",
            statement="Do not self-promote this claim.",
            depth=0,
            claim_promotion_allowed=True,
        )

    with pytest.raises(ValueError, match="external execution"):
        RecursiveDiscoveryPolicy(allow_external_execution=True)

    with pytest.raises(ValueError, match="deferred recursive proposals"):
        RecursiveDiscoveryPolicy(preserve_deferred_proposals=False)


def test_state_and_report_digests_detect_tampering():
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="provenance",
        statement="Bind recursive state and reports to canonical digests.",
    )
    state = initialize_state([seed])
    next_state, report = run_recursive_cycle(
        state,
        [_proposal(seed.node_id, "Digest-bound child")],
    )
    assert report.state_before_digest == state_digest(state)
    assert report.state_after_digest == state_digest(next_state)
    assert verify_cycle_report(report) is True

    tampered = report.model_copy(update={"deepest_depth_seen": 999})
    assert verify_cycle_report(tampered) is False

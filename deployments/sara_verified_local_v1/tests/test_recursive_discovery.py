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


def test_duplicate_children_are_not_silently_multiplied():
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
    assert len(report.duplicate_node_ids) == 1


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

import json
from pathlib import Path

from worldshepherd_sara.recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    ExpansionProposal,
    RecursiveDiscoveryPolicy,
    initialize_state,
    make_seed,
    run_recursive_cycle,
    verify_cycle_report,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_state():
    payload = _load(FIXTURES / "omega_discovery_seeds_v1.json")
    seeds = [
        make_seed(
            kind=DiscoveryKind(item["kind"]),
            domain=item["domain"],
            statement=item["statement"],
            source_refs=item.get("source_refs", []),
            confidence=float(item.get("confidence", 0.0)),
            evidence_state=DiscoveryEvidenceState(item.get("evidence_state", "UNVERIFIED")),
            cross_domain_tags=item.get("cross_domain_tags", []),
            falsification_tests=item.get("falsification_tests", []),
        )
        for item in payload["seeds"]
    ]
    return initialize_state(seeds)


SOURCE_FIXTURE_NAMES = (
    "omega_cycle_20260907_v1.json",
    "omega_cycle_20260907_science_extension_v1.json",
    "omega_cycle_20260907_release6_extension_v1.json",
)
COMBINED_FIXTURE_NAME = "omega_cycle_20260907_combined_v1.json"


def _cycle_payloads():
    return [(FIXTURES / name, _load(FIXTURES / name)) for name in SOURCE_FIXTURE_NAMES]


def _combined_payload():
    return _load(FIXTURES / COMBINED_FIXTURE_NAME)


def test_cycle_2_fixtures_validate_and_reference_known_seed_parents():
    state = _seed_state()
    seed_ids = {node.node_id for node in state.frontier}

    total = 0
    for path, payload in _cycle_payloads():
        assert payload["schema"] == "ws-omega-proposals-1", path
        for raw in payload["proposals"]:
            proposal = ExpansionProposal.model_validate(raw)
            assert proposal.parent_node_id in seed_ids, (
                f"{path.name} references unknown parent {proposal.parent_node_id}"
            )
            assert proposal.source_refs, f"{path.name} proposal lacks source refs"
            assert proposal.falsification_tests, (
                f"{path.name} proposal lacks a cheapest-useful falsification test"
            )
            total += 1

    assert total >= 20


def test_combined_cli_fixture_contains_every_source_proposal_once():
    combined = _combined_payload()
    assert combined["schema"] == "ws-omega-proposals-1"
    assert tuple(combined["source_fixture_names"]) == SOURCE_FIXTURE_NAMES
    source_proposals = [
        item
        for _path, payload in _cycle_payloads()
        for item in payload["proposals"]
    ]
    assert len(combined["proposals"]) == len(source_proposals)
    assert {
        json.dumps(item, sort_keys=True) for item in combined["proposals"]
    } == {json.dumps(item, sort_keys=True) for item in source_proposals}


def test_cycle_2_executes_without_dropping_or_promoting_proposals():
    state = _seed_state()
    proposals = [
        ExpansionProposal.model_validate(item)
        for item in _combined_payload()["proposals"]
    ]

    policy = RecursiveDiscoveryPolicy(
        parent_budget_per_cycle=64,
        max_children_per_parent=32,
        max_new_nodes_per_cycle=512,
        max_active_frontier=4096,
    )
    next_state, report = run_recursive_cycle(state, proposals, policy=policy)

    assert report.cycle_index == 1
    assert len(report.generated_node_ids) == len(proposals)
    assert report.duplicate_node_ids == []
    assert report.claim_promotion_performed is False
    assert report.external_execution_performed is False
    assert report.physical_infinity_claimed is False
    assert report.global_depth_limit is None
    assert verify_cycle_report(report) is True

    generated_ids = set(report.generated_node_ids)
    generated = [node for node in next_state.frontier if node.node_id in generated_ids]
    assert len(generated) == len(proposals)
    assert all(node.depth == 1 for node in generated)
    assert all(node.claim_promotion_allowed is False for node in generated)
    assert all(node.physical_validation_claimed is False for node in generated)
    assert all(node.external_execution_performed is False for node in generated)


def test_cycle_2_preserves_negative_and_prior_art_as_first_class_nodes():
    state = _seed_state()
    proposals = [
        ExpansionProposal.model_validate(item)
        for item in _combined_payload()["proposals"]
    ]

    next_state, report = run_recursive_cycle(
        state,
        proposals,
        policy=RecursiveDiscoveryPolicy(
            parent_budget_per_cycle=64,
            max_children_per_parent=32,
            max_new_nodes_per_cycle=512,
        ),
    )

    generated_ids = set(report.generated_node_ids)
    generated = [node for node in next_state.frontier if node.node_id in generated_ids]
    kinds = {node.kind for node in generated}
    assert DiscoveryKind.PRIOR_ART in kinds
    assert DiscoveryKind.OBSERVATION in kinds
    assert DiscoveryKind.OPPORTUNITY in kinds
    assert DiscoveryKind.STANDARD in kinds

    heavy_lift_prior_art = [
        node
        for node in generated
        if node.kind == DiscoveryKind.PRIOR_ART
        and "9.63:1" in node.statement
    ]
    assert len(heavy_lift_prior_art) == 1
    assert "did not complete a scored run" in heavy_lift_prior_art[0].statement

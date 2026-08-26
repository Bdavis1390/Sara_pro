from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.apnt import apnt_snapshot_graph, derive_apnt_decision


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "apnt_destroyer_strait_v1.json"
)


def test_synthetic_apnt_fixture_matches_expected_states_and_recovery_options():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for item in payload["timeline"]:
        decision = derive_apnt_decision(item["source_state"])
        assert decision.operational_state == item["expected_operational_state"]
        if "expected_recovery_options" in item:
            assert set(decision.recovery_options) == set(item["expected_recovery_options"])


def test_apnt_graph_preserves_all_sources_and_derived_state():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    item = payload["timeline"][2]
    decision = derive_apnt_decision(item["source_state"])
    graph = apnt_snapshot_graph(
        graph_id="apnt-fixture-t120",
        source_state=item["source_state"],
        decision=decision,
    )

    node_ids = {node.node_id for node in graph.nodes}
    assert {
        "source:gnss_primary",
        "source:ins_primary",
        "source:alt_pnt_1",
        "derived:operational_state",
        "policy:recovery_options",
    }.issubset(node_ids)
    assert len(graph.edges) == 4

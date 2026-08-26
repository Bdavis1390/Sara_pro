from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.graph_metrics import score_graph


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "mbse_legacy_fixture_v1.json"
)


def _relationship_key(item: dict[str, str]) -> str:
    return f'{item["source"]}->{item["target"]}:{item["relation"]}'


def test_mbse_fixture_ground_truth_scores_perfectly_against_itself():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    truth = payload["ground_truth"]
    entities = {item["id"] for item in truth["nodes"]}
    relationships = {_relationship_key(item) for item in truth["edges"]}

    score = score_graph(
        expected_entities=entities,
        predicted_entities=entities,
        expected_relationships=relationships,
        predicted_relationships=relationships,
    )

    assert score.entity_precision == 1.0
    assert score.entity_recall == 1.0
    assert score.relationship_precision == 1.0
    assert score.relationship_recall == 1.0


def test_mbse_fixture_artifacts_cover_each_ground_truth_relationship():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = {
        _relationship_key(item) for item in payload["ground_truth"]["edges"]
    }
    supported: set[str] = set()
    for artifact in payload["legacy_artifacts"]:
        supported.update(artifact.get("expected_support", []))

    assert expected == supported

from __future__ import annotations

from worldshepherd_sara.graph_metrics import score_graph


def test_graph_score_perfect_match():
    score = score_graph(
        expected_entities={"a", "b"},
        predicted_entities={"a", "b"},
        expected_relationships={"a->b:connects"},
        predicted_relationships={"a->b:connects"},
    )
    assert score.entity_precision == 1.0
    assert score.entity_recall == 1.0
    assert score.relationship_precision == 1.0
    assert score.relationship_recall == 1.0
    assert score.unsupported_entities == ()
    assert score.unsupported_relationships == ()


def test_graph_score_reports_unsupported_and_missed_content():
    score = score_graph(
        expected_entities={"a", "b", "c"},
        predicted_entities={"a", "b", "x"},
        expected_relationships={"a->b:connects", "b->c:feeds"},
        predicted_relationships={"a->b:connects", "b->x:feeds"},
    )
    assert score.entity_precision == 2 / 3
    assert score.entity_recall == 2 / 3
    assert score.relationship_precision == 0.5
    assert score.relationship_recall == 0.5
    assert score.unsupported_entities == ("x",)
    assert score.missed_entities == ("c",)
    assert score.unsupported_relationships == ("b->x:feeds",)
    assert score.missed_relationships == ("b->c:feeds",)

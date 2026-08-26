from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class GraphScore:
    entity_precision: float
    entity_recall: float
    relationship_precision: float
    relationship_recall: float
    unsupported_entities: tuple[str, ...]
    unsupported_relationships: tuple[str, ...]
    missed_entities: tuple[str, ...]
    missed_relationships: tuple[str, ...]


def _safe_ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 and numerator == 0 else (
        0.0 if denominator == 0 else numerator / denominator
    )


def score_graph(
    *,
    expected_entities: Iterable[str],
    predicted_entities: Iterable[str],
    expected_relationships: Iterable[str],
    predicted_relationships: Iterable[str],
) -> GraphScore:
    expected_e = set(expected_entities)
    predicted_e = set(predicted_entities)
    expected_r = set(expected_relationships)
    predicted_r = set(predicted_relationships)

    entity_true_positive = len(expected_e & predicted_e)
    relationship_true_positive = len(expected_r & predicted_r)

    return GraphScore(
        entity_precision=_safe_ratio(entity_true_positive, len(predicted_e)),
        entity_recall=_safe_ratio(entity_true_positive, len(expected_e)),
        relationship_precision=_safe_ratio(
            relationship_true_positive, len(predicted_r)
        ),
        relationship_recall=_safe_ratio(
            relationship_true_positive, len(expected_r)
        ),
        unsupported_entities=tuple(sorted(predicted_e - expected_e)),
        unsupported_relationships=tuple(sorted(predicted_r - expected_r)),
        missed_entities=tuple(sorted(expected_e - predicted_e)),
        missed_relationships=tuple(sorted(expected_r - predicted_r)),
    )

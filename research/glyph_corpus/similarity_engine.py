"""Worldshepherd glyph-corpus comparison primitives.

This module intentionally keeps structural resemblance separate from historical,
organizational and quantitative evidence. It is not a classifier of shared
origin and must not be used to promote a visual match directly into provenance.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Sequence


@dataclass(frozen=True)
class StructuralFeatures:
    """Normalized 0..1 feature similarities for one artifact pair."""

    geometry: float
    topology: float
    order: float
    handedness: float
    counts: float
    ratios: float
    cooccurrence: float


def _unit_interval(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"expected value in [0,1], got {value}")
    return float(value)


def structural_match(features: StructuralFeatures) -> float:
    """Return Structural Match (SM), never a probability of common origin."""

    for value in (
        features.geometry,
        features.topology,
        features.order,
        features.handedness,
        features.counts,
        features.ratios,
        features.cooccurrence,
    ):
        _unit_interval(value)

    return (
        0.15 * features.geometry
        + 0.25 * features.topology
        + 0.15 * features.order
        + 0.10 * features.handedness
        + 0.10 * features.counts
        + 0.10 * features.ratios
        + 0.15 * features.cooccurrence
    )


def claim_ceiling(
    *,
    structural_match_score: float,
    semantic_match: bool = False,
    chronology_contact: bool = False,
    documented_transmission: bool = False,
    organizational_primary: bool = False,
    quantitative_validated: bool = False,
) -> str:
    """Return the strongest statement allowed by the supplied evidence.

    The output is an evidence-language ceiling, not an automatic conclusion.
    A caller should still retain underlying sources, uncertainty and negative
    evidence in the LSRP record.
    """

    _unit_interval(structural_match_score)

    if quantitative_validated:
        return "supported quantitative correspondence"
    if organizational_primary:
        return "documented organizational association"
    if documented_transmission:
        return "supported historical transmission"
    if chronology_contact:
        return "possible historical relationship"
    if semantic_match:
        return "structural and semantic parallel"
    if structural_match_score >= 0.65:
        return "strong visual/structural correspondence"
    return "visual resemblance only"


def order_similarity(observed: Sequence[str], candidate: Sequence[str]) -> float:
    """Simple position-wise order agreement for equal-length motif sequences."""

    if not observed or len(observed) != len(candidate):
        raise ValueError("order sequences must be non-empty and equal length")
    return sum(a == b for a, b in zip(observed, candidate)) / len(observed)


def permutation_order_test(
    observed: Sequence[str],
    candidate: Sequence[str],
    *,
    permutations: int = 10_000,
    seed: int = 0,
) -> tuple[float, float]:
    """Compare observed sequence alignment against shuffled motif order.

    Returns `(observed_score, empirical_p_value)`. The p-value addresses order
    specificity only; it does not prove historical connection.
    """

    if permutations < 1:
        raise ValueError("permutations must be >= 1")

    observed_score = order_similarity(observed, candidate)
    rng = random.Random(seed)
    template = list(candidate)
    at_least_as_good = 0

    for _ in range(permutations):
        shuffled = template[:]
        rng.shuffle(shuffled)
        if order_similarity(observed, shuffled) >= observed_score:
            at_least_as_good += 1

    empirical_p = (at_least_as_good + 1) / (permutations + 1)
    return observed_score, empirical_p


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Return Benjamini-Hochberg FDR-adjusted p-values in original order."""

    if not p_values:
        return []

    for value in p_values:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"invalid p-value: {value}")

    n = len(p_values)
    ranked_indices = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    previous = 1.0

    for reverse_offset, index in enumerate(reversed(ranked_indices), start=1):
        rank = n - reverse_offset + 1
        q_value = min(previous, p_values[index] * n / rank)
        adjusted[index] = q_value
        previous = q_value

    return adjusted

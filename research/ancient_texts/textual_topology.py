from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
from math import inf
from typing import Callable, Sequence

@dataclass(frozen=True)
class TextUnit:
    unit_id: str
    ordinal: int | None
    text: str
    source_position: int

@dataclass(frozen=True)
class OrderConstraint:
    before: str
    after: str
    weight: float = 1.0
    rationale: str | None = None

def order_score(
    order: Sequence[str],
    constraints: Sequence[OrderConstraint],
) -> float:
    pos = {unit_id: i for i, unit_id in enumerate(order)}
    score = 0.0
    for c in constraints:
        if c.before not in pos or c.after not in pos:
            continue
        if pos[c.before] < pos[c.after]:
            score += c.weight
    return score

def ordinal_constraints(units: Sequence[TextUnit]) -> list[OrderConstraint]:
    with_ord = sorted(
        (u for u in units if u.ordinal is not None),
        key=lambda u: u.ordinal,
    )
    out: list[OrderConstraint] = []
    for left, right in zip(with_ord, with_ord[1:]):
        out.append(OrderConstraint(
            left.unit_id,
            right.unit_id,
            weight=2.0,
            rationale=f"ordinal {left.ordinal} precedes {right.ordinal}",
        ))
    return out

def displacement_cost(
    proposed_order: Sequence[str],
    units: Sequence[TextUnit],
) -> int:
    source_pos = {u.unit_id: u.source_position for u in units}
    return sum(
        abs(i - source_pos[unit_id])
        for i, unit_id in enumerate(proposed_order)
        if unit_id in source_pos
    )

def infer_order_exhaustive(
    units: Sequence[TextUnit],
    constraints: Sequence[OrderConstraint],
    max_units: int = 9,
) -> dict:
    if len(units) > max_units:
        raise ValueError("exhaustive inference limited; use constrained optimizer")
    ids = [u.unit_id for u in units]
    best_order = None
    best_score = -inf
    best_displacement = inf
    for order in permutations(ids):
        score = order_score(order, constraints)
        displacement = displacement_cost(order, units)
        if score > best_score or (
            score == best_score and displacement < best_displacement
        ):
            best_order = order
            best_score = score
            best_displacement = displacement
    return {
        "order": list(best_order) if best_order else [],
        "constraint_score": best_score,
        "displacement_cost": best_displacement,
        "claim_ceiling": "STRUCTURAL_RECONSTRUCTION_HYPOTHESIS",
    }

def validate_against_witness(
    proposed_order: Sequence[str],
    independent_witness_order: Sequence[str],
) -> dict:
    common = [
        unit for unit in proposed_order
        if unit in set(independent_witness_order)
    ]
    witness_common = [
        unit for unit in independent_witness_order
        if unit in set(proposed_order)
    ]
    exact = common == witness_common
    return {
        "exact_on_common_units": exact,
        "proposed_common": common,
        "witness_common": witness_common,
        "claim_state": (
            "INDEPENDENT_WITNESS_SUPPORT"
            if exact
            else "STRUCTURAL_RECONSTRUCTION_NOT_CONFIRMED"
        ),
    }

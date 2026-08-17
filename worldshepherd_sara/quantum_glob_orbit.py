"""Exact classical and reversible-operator model for the three established GLOB 5-position permutations.

This module formalizes a legitimate reversible computational object while preserving the
negative conclusion that these tiny permutation orbits are classically trivial. It is a
mapping/control artifact, not evidence of quantum physics or quantum advantage.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import random
from typing import Iterable

from worldshepherd_sara.quantum_glob_mapping import GlobQuantumMapping, MappingType, evaluate_glob_mapping

OPERATORS: dict[str, tuple[int, ...]] = {
    "PA": (3, 1, 5, 4, 2),
    "PB": (1, 3, 5, 2, 4),
    "PC": (1, 4, 5, 2, 3),
}


def _digest(payload: object) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + sha256(text.encode("utf-8")).hexdigest()


def validate_operator(operator: Iterable[int]) -> tuple[int, ...]:
    op = tuple(int(value) for value in operator)
    if len(op) != 5 or sorted(op) != [1, 2, 3, 4, 5]:
        raise ValueError("operator must be a permutation of positions 1..5")
    return op


def apply_operator(value: str, operator: Iterable[int]) -> str:
    op = validate_operator(operator)
    if len(value) != 5:
        raise ValueError("value must contain exactly five symbols; zero-padding must be explicit upstream")
    return "".join(value[index - 1] for index in op)


def exact_orbit(value: str, operator: Iterable[int]) -> tuple[str, ...]:
    op = validate_operator(operator)
    if len(value) != 5:
        raise ValueError("value must contain exactly five symbols")
    orbit = [value]
    current = value
    while True:
        current = apply_operator(current, op)
        if current == value:
            return tuple(orbit)
        if current in orbit:
            raise RuntimeError("position permutation entered a non-base cycle unexpectedly")
        orbit.append(current)
        if len(orbit) > 120:
            raise RuntimeError("S5 orbit exceeded mathematical upper bound")


def operator_order(operator: Iterable[int]) -> int:
    return len(exact_orbit("12345", operator))


def deterministic_null_operator(seed: int = 9675) -> tuple[int, ...]:
    values = [1, 2, 3, 4, 5]
    rng = random.Random(seed)
    rng.shuffle(values)
    candidate = tuple(values)
    if candidate in OPERATORS.values():
        values = values[1:] + values[:1]
        candidate = tuple(values)
    return validate_operator(candidate)


def build_operator_mapping(name: str, *, null_seed: int = 9675) -> GlobQuantumMapping:
    if name not in OPERATORS:
        raise KeyError(f"unknown established operator {name!r}")
    op = OPERATORS[name]
    order = operator_order(op)
    quantum_object = {
        "object_type": "reversible_position_permutation",
        "operator_name": name,
        "operator_1_indexed": list(op),
        "register_model": "five 4-bit symbol registers; position permutation only",
        "unitary_semantics": "basis-state register permutation; no arithmetic transformation of symbol values",
        "operator_order": order,
    }
    null_op = deterministic_null_operator(null_seed)
    null_id = f"GLOB-NULL-S5-{null_seed}-{_digest(list(null_op)).split(':', 1)[1][:12]}"
    return GlobQuantumMapping(
        mapping_id=f"GLOB-{name}-REV-PERM-001",
        mapping_type=MappingType.ORACLE,
        input_contract="one exact 5-symbol basis string; any zero-padding is an explicitly derived representation",
        output_contract="basis string after one reversible position-permutation application; repeated application yields exact finite orbit",
        measurable_target="verify operator action and return period against exhaustive classical orbit traversal",
        classical_baseline=f"direct five-index permutation with exhaustive orbit traversal; established operator order={order}",
        classical_complexity=f"O(5) per application and O({order}*5) for a complete orbit; tiny constant-size exact baseline",
        quantum_object_digest=_digest(quantum_object),
        construction_cost="encode five symbol registers and a fixed register-permutation/SWAP network; construction overhead exceeds the direct classical operation for these instances",
        verification_method="compare every measured basis-state transition and return period with exact deterministic classical permutation/orbit output",
        resource_estimate_id=None,
        null_model_id=null_id,
        classical_dominates=True,
        quantum_execution_rationale="No QPU run is recommended for the established 5-position operators absent a larger mission problem whose complexity is not dominated by direct classical permutation traversal.",
    )


def mapping_report() -> dict[str, object]:
    rows = []
    for name in OPERATORS:
        mapping = build_operator_mapping(name)
        decision = evaluate_glob_mapping(mapping)
        rows.append({
            "operator": name,
            "permutation_1_indexed": list(OPERATORS[name]),
            "operator_order": operator_order(OPERATORS[name]),
            "mapping": asdict(mapping),
            "decision": asdict(decision),
        })
    return {
        "schema_version": "1.0",
        "operators": rows,
        "claim_control": (
            "The established PA/PB/PC position permutations now have explicit reversible computational mappings. "
            "All remain classical controls: mapping validity does not justify QPU execution and does not turn numerical structure into quantum evidence."
        ),
    }

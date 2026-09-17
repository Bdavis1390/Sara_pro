"""Deterministic analysis helpers for source-controlled Enochian transcriptions.

These functions characterize structure. They do not infer supernatural origin,
semantic truth, historical transmission, or physical-frequency effects.
"""

from __future__ import annotations

from collections import Counter
from math import log2
from typing import Iterable, Sequence


def shannon_entropy(symbols: Iterable[str]) -> float:
    items = list(symbols)
    if not items:
        return 0.0
    counts = Counter(items)
    n = len(items)
    return -sum((c / n) * log2(c / n) for c in counts.values())


def ngrams(sequence: Sequence[str], n: int) -> Counter[tuple[str, ...]]:
    if n <= 0:
        raise ValueError("n must be positive")
    return Counter(tuple(sequence[i : i + n]) for i in range(len(sequence) - n + 1))


def validate_rectangular_grid(grid: Sequence[Sequence[str]]) -> tuple[int, int]:
    if not grid:
        raise ValueError("grid is empty")
    widths = {len(row) for row in grid}
    if 0 in widths or len(widths) != 1:
        raise ValueError("grid must be non-empty and rectangular")
    return len(grid), widths.pop()


def row_major(grid: Sequence[Sequence[str]]) -> list[str]:
    validate_rectangular_grid(grid)
    return [cell for row in grid for cell in row]


def column_major(grid: Sequence[Sequence[str]]) -> list[str]:
    rows, cols = validate_rectangular_grid(grid)
    return [grid[r][c] for c in range(cols) for r in range(rows)]


def boustrophedon(grid: Sequence[Sequence[str]]) -> list[str]:
    validate_rectangular_grid(grid)
    out: list[str] = []
    for i, row in enumerate(grid):
        out.extend(row if i % 2 == 0 else reversed(row))
    return out


def main_diagonal(grid: Sequence[Sequence[str]]) -> list[str]:
    rows, cols = validate_rectangular_grid(grid)
    return [grid[i][i] for i in range(min(rows, cols))]


def anti_diagonal(grid: Sequence[Sequence[str]]) -> list[str]:
    rows, cols = validate_rectangular_grid(grid)
    return [grid[i][cols - 1 - i] for i in range(min(rows, cols))]


def rotate90(grid: Sequence[Sequence[str]]) -> list[list[str]]:
    validate_rectangular_grid(grid)
    return [list(row) for row in zip(*grid[::-1])]


def reflect_horizontal(grid: Sequence[Sequence[str]]) -> list[list[str]]:
    validate_rectangular_grid(grid)
    return [list(reversed(row)) for row in grid]


def symbol_profile(grid: Sequence[Sequence[str]]) -> dict[str, object]:
    rows, cols = validate_rectangular_grid(grid)
    flat = row_major(grid)
    counts = Counter(flat)
    return {
        "rows": rows,
        "cols": cols,
        "cells": rows * cols,
        "unique_symbols": len(counts),
        "entropy_bits_per_symbol": shannon_entropy(flat),
        "frequencies": dict(sorted(counts.items())),
    }


def traversal_profiles(grid: Sequence[Sequence[str]]) -> dict[str, dict[str, object]]:
    """Return profiles for pre-declared traversal families.

    This function intentionally avoids searching arbitrary paths. Exploratory path
    mining creates severe multiple-comparison risk and must be handled separately
    with permutation/null models and FDR correction.
    """
    traversals = {
        "row_major": row_major(grid),
        "column_major": column_major(grid),
        "boustrophedon": boustrophedon(grid),
        "main_diagonal": main_diagonal(grid),
        "anti_diagonal": anti_diagonal(grid),
    }
    return {
        name: {
            "length": len(seq),
            "entropy": shannon_entropy(seq),
            "bigrams": {"".join(k): v for k, v in ngrams(seq, 2).most_common(20)},
        }
        for name, seq in traversals.items()
    }


def normalized_hamming(a: Sequence[str], b: Sequence[str]) -> float:
    if len(a) != len(b):
        raise ValueError("sequences must have equal length")
    if not a:
        return 0.0
    return sum(x != y for x, y in zip(a, b)) / len(a)


def symmetry_scores(grid: Sequence[Sequence[str]]) -> dict[str, float]:
    flat = row_major(grid)
    h = row_major(reflect_horizontal(grid))
    r90 = rotate90(grid)
    scores = {"horizontal_reflection_similarity": 1.0 - normalized_hamming(flat, h)}
    rows, cols = validate_rectangular_grid(grid)
    if rows == cols:
        scores["rotation_90_similarity"] = 1.0 - normalized_hamming(flat, row_major(r90))
    return scores

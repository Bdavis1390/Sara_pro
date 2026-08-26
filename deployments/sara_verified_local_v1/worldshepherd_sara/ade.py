from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class Expr:
    op: str
    value: float | None = None
    left: "Expr | None" = None
    right: "Expr | None" = None

    def evaluate(self, x: float) -> float:
        if self.op == "x":
            return x
        if self.op == "const":
            assert self.value is not None
            return self.value
        if self.op == "add":
            assert self.left is not None and self.right is not None
            return self.left.evaluate(x) + self.right.evaluate(x)
        if self.op == "sub":
            assert self.left is not None and self.right is not None
            return self.left.evaluate(x) - self.right.evaluate(x)
        if self.op == "mul":
            assert self.left is not None and self.right is not None
            return self.left.evaluate(x) * self.right.evaluate(x)
        if self.op == "square":
            assert self.left is not None
            value = self.left.evaluate(x)
            return value * value
        raise ValueError(f"unknown op: {self.op}")

    def complexity(self) -> int:
        if self.op in {"x", "const"}:
            return 1
        if self.op == "square":
            assert self.left is not None
            return 1 + self.left.complexity()
        assert self.left is not None and self.right is not None
        return 1 + self.left.complexity() + self.right.complexity()

    def text(self) -> str:
        if self.op == "x":
            return "x"
        if self.op == "const":
            assert self.value is not None
            return str(int(self.value)) if self.value.is_integer() else str(self.value)
        if self.op == "square":
            assert self.left is not None
            return f"square({self.left.text()})"
        assert self.left is not None and self.right is not None
        symbol = {"add": "+", "sub": "-", "mul": "*"}[self.op]
        return f"({self.left.text()} {symbol} {self.right.text()})"

    def canonical(self) -> str:
        if self.op in {"x", "const"}:
            return self.text()
        if self.op == "square":
            assert self.left is not None
            return f"square:{self.left.canonical()}"
        assert self.left is not None and self.right is not None
        left = self.left.canonical()
        right = self.right.canonical()
        if self.op in {"add", "mul"} and right < left:
            left, right = right, left
        return f"{self.op}:{left}:{right}"


@dataclass(frozen=True)
class DiscoveryResult:
    expression: Expr
    mse: float
    baseline_mse: float
    improvement_ratio: float
    evaluated_candidates: int

    @property
    def human_interpretable(self) -> bool:
        return True


def _mse(expr: Expr, samples: list[tuple[float, float]]) -> float:
    total = 0.0
    for x, target in samples:
        try:
            observed = expr.evaluate(x)
        except (OverflowError, ZeroDivisionError, ValueError):
            return float("inf")
        if not isfinite(observed):
            return float("inf")
        delta = observed - target
        total += delta * delta
    return total / max(len(samples), 1)


def _rank_key(expr: Expr, samples: list[tuple[float, float]]) -> tuple[float, int, str]:
    return (_mse(expr, samples), expr.complexity(), expr.canonical())


def discover_expression(
    samples: Iterable[tuple[float, float]],
    *,
    constants: tuple[int, ...] = (-2, -1, 0, 1, 2),
    max_depth: int = 2,
    beam_width: int = 256,
) -> DiscoveryResult:
    """Deterministic bounded symbolic search for interpretable arithmetic rules.

    This is a research kernel for synthetic discovery benchmarks. It is not
    evidence of state-of-the-art algorithm discovery or DARPA SPEED DIAL D2P2
    qualification.
    """
    data = [(float(x), float(y)) for x, y in samples]
    if not data:
        raise ValueError("at least one sample is required")

    x_expr = Expr("x")
    terminals = [x_expr] + [Expr("const", value=float(c)) for c in constants]
    baseline_mse = _mse(x_expr, data)
    pool: dict[str, Expr] = {expr.canonical(): expr for expr in terminals}
    evaluated: set[str] = set(pool)
    frontier = list(pool.values())

    for _depth in range(max_depth):
        candidates: dict[str, Expr] = dict(pool)
        for expr in frontier:
            squared = Expr("square", left=expr)
            candidates[squared.canonical()] = squared

        base = list(pool.values())
        for left in frontier:
            for right in base:
                for op in ("add", "sub", "mul"):
                    candidate = Expr(op, left=left, right=right)
                    candidates[candidate.canonical()] = candidate

        ranked = sorted(candidates.values(), key=lambda expr: _rank_key(expr, data))
        pool = {expr.canonical(): expr for expr in ranked[:beam_width]}
        frontier = list(pool.values())
        evaluated.update(candidates)

    best = min(pool.values(), key=lambda expr: _rank_key(expr, data))
    best_mse = _mse(best, data)
    if baseline_mse == 0.0:
        improvement = 1.0 if best_mse == 0.0 else 0.0
    else:
        improvement = baseline_mse / max(best_mse, 1e-12)

    return DiscoveryResult(
        expression=best,
        mse=best_mse,
        baseline_mse=baseline_mse,
        improvement_ratio=improvement,
        evaluated_candidates=len(evaluated),
    )

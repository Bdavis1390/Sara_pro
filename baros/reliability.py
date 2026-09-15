"""Statistically auditable bounded-reliability gate for BAROS research software.

NON-CLINICAL. This module estimates only the probability that the bounded
research-software pipeline satisfies its declared synthetic acceptance criteria
under a predeclared synthetic case distribution. It does not estimate clinical
safety, effectiveness, treatment success, physical dose accuracy, regulatory
acceptability, or patient outcome probability.

For zero observed failures in n Bernoulli trials, the exact one-sided lower
Clopper-Pearson confidence bound for success probability p is:

    p_lower = alpha ** (1 / n)

where confidence = 1 - alpha.

The BAROS gate defaults to n=1000 and confidence=99.9%. If all 1000 cases pass,
the exact one-sided lower confidence bound exceeds 98.7% with substantial
margin. Any observed failure causes this zero-failure gate to fail closed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random
from typing import Any

from .pipeline import SyntheticCase, run_synthetic_pipeline


DEFAULT_CASE_COUNT = 1000
DEFAULT_CONFIDENCE = 0.999
DEFAULT_TARGET_PROBABILITY = 0.987
DEFAULT_MASTER_SEED = 96759530
DISTRIBUTION_VERSION = "baros.synthetic-reliability.v1"


@dataclass(frozen=True)
class ReliabilityCaseResult:
    case_index: int
    case_seed: int
    passed: bool
    evidence_sha256: str
    tumor_survival_objective: float
    hard_constraints_satisfied: bool


@dataclass(frozen=True)
class ReliabilityReport:
    distribution_version: str
    master_seed: int
    cases: int
    successes: int
    failures: int
    confidence: float
    target_probability: float
    lower_confidence_bound: float
    gate_passed: bool
    case_results_sha256: str
    failed_case_indices: tuple[int, ...]


def zero_failure_lower_bound(*, trials: int, confidence: float) -> float:
    """Exact one-sided lower confidence bound when every trial succeeds."""
    if not isinstance(trials, int) or trials <= 0:
        raise ValueError("trials must be a positive integer")
    confidence = float(confidence)
    if not math.isfinite(confidence) or not (0.0 < confidence < 1.0):
        raise ValueError("confidence must be within (0, 1)")
    alpha = 1.0 - confidence
    return alpha ** (1.0 / trials)


def minimum_zero_failure_trials(*, target_probability: float, confidence: float) -> int:
    """Smallest zero-failure sample count whose lower bound clears target."""
    target = float(target_probability)
    confidence = float(confidence)
    if not math.isfinite(target) or not (0.0 < target < 1.0):
        raise ValueError("target_probability must be within (0, 1)")
    if not math.isfinite(confidence) or not (0.0 < confidence < 1.0):
        raise ValueError("confidence must be within (0, 1)")
    return math.ceil(math.log(1.0 - confidence) / math.log(target))


def _draw_case(case_seed: int) -> SyntheticCase:
    """Draw one valid synthetic case from the predeclared v1 distribution.

    Distribution boundaries are intentionally bounded away from singular and
    clinically interpreted values. They exercise software behavior only.
    """
    rng = random.Random(case_seed)

    beamlets = 4
    tumor_voxels = (0, 1)
    oar_voxels = (2, 3)

    influence: list[tuple[float, ...]] = []
    for _ in range(beamlets):
        tumor_1 = rng.uniform(0.45, 1.35)
        tumor_2 = rng.uniform(0.45, 1.35)
        oar_1 = rng.uniform(0.015, 0.16)
        oar_2 = rng.uniform(0.015, 0.16)
        influence.append((tumor_1, tumor_2, oar_1, oar_2))

    alpha = (rng.uniform(0.15, 0.45), rng.uniform(0.15, 0.45))
    beta = (rng.uniform(0.01, 0.06), rng.uniform(0.01, 0.06))
    clonogens = (rng.uniform(50.0, 250.0), rng.uniform(50.0, 250.0))
    oar_limits = {
        oar_voxels[0]: rng.uniform(0.60, 1.80),
        oar_voxels[1]: rng.uniform(0.60, 1.80),
    }

    return SyntheticCase(
        influence=tuple(influence),
        tumor_voxels=tumor_voxels,
        alpha_per_gy=alpha,
        beta_per_gy2=beta,
        clonogen_counts=clonogens,
        oar_max_gy=oar_limits,
        ntcp_d50_gy=rng.uniform(1.8, 3.5),
        ntcp_slope_per_gy=rng.uniform(0.5, 2.5),
        initial_weights=(0.0, 0.0, 0.0, 0.0),
        weight_max=rng.uniform(8.0, 20.0),
        step_size=rng.uniform(0.5, 4.0),
    )


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_reliability_gate(
    *,
    cases: int = DEFAULT_CASE_COUNT,
    confidence: float = DEFAULT_CONFIDENCE,
    target_probability: float = DEFAULT_TARGET_PROBABILITY,
    master_seed: int = DEFAULT_MASTER_SEED,
    commit_sha: str = "UNPINNED",
) -> ReliabilityReport:
    """Run the predeclared bounded reliability population and fail closed.

    The statistical probability statement is permitted only when there are zero
    observed failures and the exact one-sided lower confidence bound meets the
    target probability. The case generator and seed are included for exact
    reproducibility but are not independent clinical evidence.
    """
    if not isinstance(cases, int) or cases <= 0:
        raise ValueError("cases must be a positive integer")
    required = minimum_zero_failure_trials(
        target_probability=target_probability,
        confidence=confidence,
    )
    if cases < required:
        raise ValueError(
            f"cases={cases} is insufficient; at least {required} zero-failure trials are required"
        )

    seed_rng = random.Random(int(master_seed))
    results: list[ReliabilityCaseResult] = []

    for index in range(cases):
        case_seed = seed_rng.randrange(0, 2**63)
        case = _draw_case(case_seed)
        evidence = run_synthetic_pipeline(case, commit_sha=commit_sha)
        results.append(
            ReliabilityCaseResult(
                case_index=index,
                case_seed=case_seed,
                passed=bool(evidence["passed"]),
                evidence_sha256=str(evidence["evidence_sha256"]),
                tumor_survival_objective=float(evidence["result"]["tumor_survival_objective"]),
                hard_constraints_satisfied=bool(evidence["pass_conditions"]["hard_constraints_satisfied"]),
            )
        )

    successes = sum(item.passed for item in results)
    failures = cases - successes
    lower = zero_failure_lower_bound(trials=cases, confidence=confidence) if failures == 0 else 0.0
    target = float(target_probability)
    gate_passed = failures == 0 and lower >= target
    failed_indices = tuple(item.case_index for item in results if not item.passed)
    results_payload = [asdict(item) for item in results]

    return ReliabilityReport(
        distribution_version=DISTRIBUTION_VERSION,
        master_seed=int(master_seed),
        cases=cases,
        successes=successes,
        failures=failures,
        confidence=float(confidence),
        target_probability=target,
        lower_confidence_bound=lower,
        gate_passed=gate_passed,
        case_results_sha256=_canonical_hash(results_payload),
        failed_case_indices=failed_indices,
    )


def report_as_dict(report: ReliabilityReport) -> dict[str, Any]:
    return asdict(report)

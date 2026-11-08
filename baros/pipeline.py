"""End-to-end synthetic BAROS research pipeline.

NON-CLINICAL: deterministic verification only. No patient data, DICOM, TPS, or
clinical dose engine is used here. This module must not be used for patient care.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .dose import dose_from_influence, hard_max_constraints
from .models import logistic_ntcp, lq_survival, poisson_tcp
from .provenance import runtime_provenance
from .reference_optimizer import optimize_synthetic, tumor_survival_objective


SCHEMA_VERSION = "baros.synthetic-evidence.v2"


@dataclass(frozen=True)
class SyntheticCase:
    influence: tuple[tuple[float, ...], ...]
    tumor_voxels: tuple[int, ...]
    alpha_per_gy: tuple[float, ...]
    beta_per_gy2: tuple[float, ...]
    clonogen_counts: tuple[float, ...]
    oar_max_gy: dict[int, float]
    ntcp_d50_gy: float
    ntcp_slope_per_gy: float
    initial_weights: tuple[float, ...]
    weight_max: float
    step_size: float


def default_synthetic_case() -> SyntheticCase:
    return SyntheticCase(
        influence=(
            (1.00, 0.70, 0.30, 0.10),
            (0.60, 1.00, 0.20, 0.15),
            (0.35, 0.45, 0.10, 0.40),
        ),
        tumor_voxels=(0, 1),
        alpha_per_gy=(0.30, 0.25),
        beta_per_gy2=(0.03, 0.03),
        clonogen_counts=(100.0, 100.0),
        oar_max_gy={2: 2.0, 3: 2.0},
        ntcp_d50_gy=2.5,
        ntcp_slope_per_gy=2.0,
        initial_weights=(0.0, 0.0, 0.0),
        weight_max=20.0,
        step_size=5.0,
    )


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _case_dict(case: SyntheticCase) -> dict[str, Any]:
    raw = asdict(case)
    raw["oar_max_gy"] = {str(k): v for k, v in sorted(case.oar_max_gy.items())}
    return raw


def run_synthetic_pipeline(case: SyntheticCase | None = None, *, commit_sha: str = "UNPINNED") -> dict[str, Any]:
    case = case or default_synthetic_case()
    case_payload = _case_dict(case)

    baseline_dose = dose_from_influence(case.initial_weights, case.influence)
    baseline_objective = tumor_survival_objective(
        baseline_dose, case.tumor_voxels, case.alpha_per_gy, case.beta_per_gy2
    )

    result = optimize_synthetic(
        influence=case.influence,
        tumor_voxels=case.tumor_voxels,
        alpha_per_gy=case.alpha_per_gy,
        beta_per_gy2=case.beta_per_gy2,
        oar_max_gy=case.oar_max_gy,
        initial_weights=case.initial_weights,
        weight_max=case.weight_max,
        step_size=case.step_size,
        max_iterations=200,
    )

    feasible, failures = hard_max_constraints(result.dose_gy, case.oar_max_gy)
    survivals = [
        lq_survival(result.dose_gy[idx], a, b)
        for idx, a, b in zip(case.tumor_voxels, case.alpha_per_gy, case.beta_per_gy2)
    ]
    tcp = poisson_tcp(case.clonogen_counts, survivals)
    oar_doses = [result.dose_gy[idx] for idx in sorted(case.oar_max_gy)]
    oar_effective = sum(oar_doses) / len(oar_doses)
    ntcp = logistic_ntcp(oar_effective, case.ntcp_d50_gy, case.ntcp_slope_per_gy)

    pass_conditions = {
        "optimizer_improved_objective": result.objective < baseline_objective,
        "hard_constraints_satisfied": feasible,
        "result_finite": all(x == x and abs(x) != float("inf") for x in result.dose_gy),
    }
    passed = all(pass_conditions.values())

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "claim_state": "SIMULATED_ONLY",
        "patient_care_allowed": False,
        "commit_sha": commit_sha,
        "runtime_provenance": runtime_provenance(),
        "case_sha256": _canonical_hash(case_payload),
        "case": case_payload,
        "baseline": {
            "dose_gy": list(baseline_dose),
            "tumor_survival_objective": baseline_objective,
        },
        "result": {
            "weights": list(result.weights),
            "dose_gy": list(result.dose_gy),
            "tumor_survival_objective": result.objective,
            "iterations": result.iterations,
            "converged": result.converged,
            "synthetic_tcp": tcp,
            "synthetic_ntcp": ntcp,
        },
        "pass_conditions": pass_conditions,
        "constraint_failures": failures,
        "passed": passed,
        "limitations": [
            "synthetic influence matrix only",
            "no validated clinical TPS or independent clinical dose-engine integration",
            "no formal DICOM conformance certification or multi-vendor interoperability evidence",
            "no measurement-based DVH/gamma/phantom QA evidence",
            "no validated deformable dose accumulation",
            "no retrospective or prospective clinical evidence",
            "not for patient care",
        ],
    }
    evidence["evidence_sha256"] = _canonical_hash(evidence)
    return evidence

"""Generate closure packages for every quantum lane below the 97/100 target."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from worldshepherd_sara.quantum_mission_readiness import (
    MISSION_READY_TARGET,
    current_quantum_mission_calibration,
)


_INTERNAL_COMPLETE: dict[str, tuple[str, ...]] = {
    "SARA-QRF": (
        "evidence-gated quantum governance",
        "ideal/noisy Qiskit execution",
        "SARA evidence-registry bridge",
        "credential-gated IBM Runtime adapter",
        "Microsoft QDK resource-estimator integration",
        "PQC source inventory and private-key hard fail",
        "97/100 mission-readiness release gate",
    ),
    "WS-APNT": (
        "quantum sensing benchmark contract",
        "truth-reference and uncertainty requirements",
        "PQC migration lane",
        "97/100 mission-readiness release gate",
    ),
    "WS-ALTI": (
        "quantum materials benchmark contract",
        "classical-reference requirements",
        "fault-tolerant resource-estimate requirement",
        "97/100 mission-readiness release gate",
    ),
    "WS-METASURFACE": (
        "exact classical baseline on frozen QUBO surrogate",
        "ideal/noisy QAOA execution",
        "full-wave physics authority preserved",
        "97/100 mission-readiness release gate",
    ),
    "WS-AUTONOMOUS-LOGISTICS": (
        "exact classical baseline on frozen assignment surrogate",
        "ideal/noisy QAOA execution",
        "feasibility and latency/cost metrics retained",
        "97/100 mission-readiness release gate",
    ),
    "WS-EM-PROPULSION": (
        "quantum materials/metrology-only claim boundary",
        "classical/null-control requirements",
        "97/100 mission-readiness release gate",
    ),
    "WS-GLOB": (
        "formal oracle/Hamiltonian/objective mapping gate",
        "classical enumeration/null-model requirement",
        "97/100 mission-readiness release gate",
    ),
}

_EXTERNAL_REQUIRED: dict[str, tuple[str, ...]] = {
    "SARA-QRF": (
        "named real-QPU execution of QRF-BELL-001 with retained job/backend/calibration/result provenance",
        "repeat and cross-backend/provider reproduction",
        "measured queue, cost, failure, retry, and degraded-state behavior through SARA",
        "hardware-in-loop and relevant-environment operational demonstration",
    ),
    "WS-APNT": (
        "named calibrated quantum sensor or partner dataset",
        "truth-reference comparison with uncertainty budget",
        "hardware-in-loop degraded/denied-reference test",
        "relevant-environment operational demonstration",
    ),
    "WS-ALTI": (
        "freeze a physically specified Al-Ti-Mg-Sc-Zr structure/active-space Hamiltonian",
        "execute HF/exact-active-space/DFT reference comparison",
        "QPU or estimator-backed quantum chemistry execution where justified",
        "correlate calculation with coupon/material characterization before mission claims",
    ),
    "WS-METASURFACE": (
        "calibrate reduced-order tile objective to full-wave Maxwell/FEM/FDTD data",
        "benchmark QAOA against exhaustive/MILP/CP-SAT on the same calibrated family",
        "execute real-QPU trials with queue/cost/noise included",
        "hardware-in-loop RF test and relevant-environment demonstration",
    ),
    "WS-AUTONOMOUS-LOGISTICS": (
        "freeze a mission-relevant routing/assignment/scheduling instance family",
        "benchmark against CP-SAT/MILP and strong heuristic under identical end-to-end budget",
        "execute real-QPU trials including queue/communications/cost",
        "degraded-state hardware-in-loop and relevant-environment demonstration",
    ),
    "WS-EM-PROPULSION": (
        "freeze project-specific materials/metrology benchmark",
        "execute classical and quantum materials/sensing comparison",
        "retain calibrated force/field/thermal null controls",
        "any propulsion claim remains separately gated by reproducible physical force evidence",
    ),
    "WS-GLOB": (
        "produce a legitimate measurable oracle/Hamiltonian/sampling/search/optimization mapping",
        "show classical complexity and null-model baseline",
        "run resource estimate before QPU use",
        "QPU execution is justified only if the formal computational mapping survives review",
    ),
}


def generate_closure_packages() -> dict[str, Any]:
    packages = []
    for decision in current_quantum_mission_calibration():
        row = asdict(decision)
        project_id = decision.project_id
        row["internal_completed"] = list(_INTERNAL_COMPLETE[project_id])
        row["external_evidence_required"] = list(_EXTERNAL_REQUIRED[project_id])
        row["internal_closure_status"] = "IMPLEMENTED_AND_CI_GATED"
        row["mission_closure_status"] = "PASS_97" if decision.meets_target else "BLOCKED_ON_EVIDENCE"
        row["acceptance_rule"] = (
            f"Mission readiness must be >= {MISSION_READY_TARGET}/100 and separately authorized; "
            "internal implementation alone cannot satisfy missing external evidence."
        )
        packages.append(row)

    return {
        "schema_version": "1.0",
        "target": MISSION_READY_TARGET,
        "policy": "Every quantum lane below 97 is a hard NO-GO and remains in active closure.",
        "internal_closure": "All currently implementable software/governance pathways are CI-gated; external evidence is not fabricated.",
        "packages": packages,
    }

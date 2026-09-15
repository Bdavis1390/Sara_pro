"""Generate closure packages for Worldshepherd quantum lanes below the 97 target."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from worldshepherd_sara.quantum_mission_readiness import MISSION_READY_TARGET, current_quantum_mission_calibration

_INTERNAL_COMPLETE: dict[str, tuple[str, ...]] = {
    "SARA-QRF": ("evidence-gated quantum governance", "ideal/noisy Qiskit execution", "SARA evidence-registry bridge", "credential-gated IBM Runtime adapter", "credential-gated IonQ v0.4 adapter", "provider-neutral gate-model execution schema", "Microsoft QDK resource-estimator integration and sensitivity envelope", "PQC source inventory and private-key hard fail", "97/100 mission-readiness release gate"),
    "WS-APNT": ("quantum sensing benchmark contract", "truth-reference and uncertainty requirements", "PQC migration lane", "97/100 mission-readiness release gate"),
    "WS-ALTI": ("quantum materials benchmark contract", "classical-reference requirements", "fault-tolerant resource-estimate requirement", "97/100 mission-readiness release gate"),
    "WS-METASURFACE": ("exact classical baseline on frozen QUBO surrogate", "ideal/noisy QAOA execution", "UC06 Palace six-smoke runtime evidence and 18-point historical comparison identified", "full-wave physics authority and fail-closed calibration validator preserved", "97/100 mission-readiness release gate"),
    "WS-AUTONOMOUS-LOGISTICS": ("exact classical baseline on frozen assignment surrogate", "ideal/noisy QAOA execution", "OR-Tools CP-SAT strong comparator capability with 3/3 controlled instances optimal", "feasibility and latency/cost metrics retained", "97/100 mission-readiness release gate"),
    "WS-EM-PROPULSION": ("quantum materials/metrology-only claim boundary", "classical/null-control requirements", "97/100 mission-readiness release gate"),
    "WS-GLOB": ("exact PA/PB/PC orbit controls", "explicit reversible position-permutation mappings", "deterministic null-operator control", "mapping-validity versus QPU-justification separation", "classical-dominance hold for the established fixed operators"),
}

_EXTERNAL_REQUIRED: dict[str, tuple[str, ...]] = {
    "SARA-QRF": ("named real-QPU execution of QRF-BELL-001 with retained job/backend/calibration/result provenance", "repeat and cross-backend/provider reproduction", "measured queue, cost, failure, retry, and degraded-state behavior through SARA", "hardware-in-loop and relevant-environment operational demonstration"),
    "WS-APNT": ("named calibrated quantum sensor or partner dataset", "truth-reference comparison with uncertainty budget", "hardware-in-loop degraded/denied-reference test", "relevant-environment operational demonstration"),
    "WS-ALTI": ("freeze a physically specified Al-Ti-Mg-Sc-Zr structure/active-space Hamiltonian", "execute HF/exact-active-space/DFT reference comparison", "QPU or estimator-backed quantum chemistry execution where justified", "correlate calculation with coupon/material characterization before mission claims"),
    "WS-METASURFACE": ("resolve the failed UC06 frozen convergence gate and establish numerical/semantic equivalence on retained Palace evidence", "complete the authorized full-wave correlation campaign including VNA correlation where required by the frozen protocol", "calibrate the reduced-order tile objective to accepted retained full-wave data", "benchmark strong classical and quantum challengers on the same calibrated family before hardware trials", "hardware-in-loop RF test and relevant-environment demonstration"),
    "WS-AUTONOMOUS-LOGISTICS": ("freeze a mission-relevant routing/assignment/scheduling instance family", "execute the implemented CP-SAT comparator across the full mission family under identical end-to-end budget", "execute real-QPU/annealing trials only where the frozen formulation remains justified", "degraded-state hardware-in-loop and relevant-environment demonstration"),
    "WS-EM-PROPULSION": ("freeze project-specific materials/metrology benchmark", "execute classical and quantum materials/sensing comparison", "retain calibrated force/field/thermal null controls", "any propulsion claim remains separately gated by reproducible physical force evidence"),
    "WS-GLOB": (),
}


def generate_closure_packages() -> dict[str, Any]:
    packages = []
    for decision in current_quantum_mission_calibration():
        row = asdict(decision)
        project_id = decision.project_id
        held_classically = decision.closure_status == "QUANTUM_EXECUTION_NOT_JUSTIFIED"
        row["internal_completed"] = list(_INTERNAL_COMPLETE[project_id])
        row["external_evidence_required"] = list(_EXTERNAL_REQUIRED[project_id])
        row["internal_closure_status"] = "IMPLEMENTED_AND_CI_GATED"
        if decision.meets_target:
            row["mission_closure_status"] = "PASS_97"
        elif held_classically:
            row["mission_closure_status"] = "HELD_CLASSICAL_DOMINANCE"
        else:
            row["mission_closure_status"] = "BLOCKED_ON_EVIDENCE"
        if held_classically:
            row["acceptance_rule"] = (
                "Quantum execution remains closed for the established fixed operators because the exact classical baseline dominates. "
                "Reopen only for a materially different nontrivial problem with a frozen measurable objective, classical/null baseline, and fresh review."
            )
        else:
            row["acceptance_rule"] = (
                f"Mission readiness must be >= {MISSION_READY_TARGET}/100 and separately authorized; internal implementation alone cannot satisfy missing external evidence."
            )
        packages.append(row)

    return {
        "schema_version": "1.1",
        "target": MISSION_READY_TARGET,
        "policy": "Every quantum lane below 97 is a hard NO-GO for mission release. A quantum-execution lane may be held rather than actively closed when a valid mapping is classically dominated and QPU use is not scientifically justified.",
        "internal_closure": "All currently implementable software/governance pathways are CI-gated; external evidence is not fabricated.",
        "packages": packages,
    }

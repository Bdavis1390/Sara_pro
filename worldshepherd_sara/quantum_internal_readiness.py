"""Audit completion of internally controllable Quantum Readiness Fabric controls.

This metric is deliberately separate from mission readiness. It answers whether the
software, governance, test, evidence, and intake mechanisms that Worldshepherd can
implement without external hardware/data are complete. It cannot raise a mission
readiness score past its external-evidence cap.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

INTERNAL_TARGET = 97

@dataclass(frozen=True)
class InternalControl:
    control_id: str
    source_paths: tuple[str, ...]
    test_paths: tuple[str, ...]
    purpose: str

CONTROLS: tuple[InternalControl, ...] = (
    InternalControl("QRF-GOV", ("worldshepherd_sara/quantum_readiness.py",), ("tests/test_quantum_readiness.py",), "claim/evidence governance"),
    InternalControl("QRF-SIM", ("worldshepherd_sara/quantum_qiskit.py", "benchmarks/quantum/bell_qasm3.qasm"), ("tests/test_quantum_qiskit.py",), "ideal/noisy circuit execution"),
    InternalControl("QRF-EVID", ("worldshepherd_sara/quantum_evidence.py",), ("tests/test_quantum_evidence.py",), "machine-readable evidence and digests"),
    InternalControl("QRF-SARA", ("worldshepherd_sara/quantum_sara_bridge.py",), ("tests/test_quantum_sara_bridge.py",), "SARA evidence-registry integration"),
    InternalControl("QRF-QPU-IBM", ("worldshepherd_sara/quantum_ibm.py", "scripts/run_ibm_qpu_bell.py"), ("tests/test_quantum_ibm.py",), "credential-gated IBM gate-model real-QPU path"),
    InternalControl("QRF-QPU-PROVIDER-SCHEMA", ("worldshepherd_sara/quantum_provider.py",), ("tests/test_quantum_provider.py",), "provider-neutral gate-model hardware execution normalization for cross-provider reproduction"),
    InternalControl("QRF-QPU-IONQ", ("worldshepherd_sara/quantum_ionq.py", "scripts/run_ionq_qpu_bell.py"), ("tests/test_quantum_ionq.py",), "credential-gated IonQ v0.4 trapped-ion gate-model path normalized to the provider-neutral evidence schema"),
    InternalControl("QRF-DWAVE", ("worldshepherd_sara/quantum_dwave.py", "scripts/run_dwave_qubo.py", "requirements-quantum-dwave.txt"), ("tests/test_quantum_dwave.py",), "credential-gated D-Wave quantum-annealing backend with solver/working-graph, embedding, timing and mission-baseline provenance"),
    InternalControl("QRF-BRAKET", ("worldshepherd_sara/quantum_braket.py",), ("tests/test_quantum_braket.py",), "Amazon Braket Hybrid Job evidence contract retaining device/provider, container/source/result/program identities, queue/runtime/cost and sampled distributions"),
    InternalControl("QRF-CUDAQ", ("worldshepherd_sara/quantum_cudaq.py", "scripts/run_cudaq_bell.py", "requirements-quantum-cudaq.txt"), ("tests/test_quantum_cudaq.py",), "CUDA-Q provider-neutral portable execution layer that cannot self-promote hardware-capable targets to external-QPU evidence"),
    InternalControl("QRF-QRE", ("worldshepherd_sara/quantum_microsoft_resource.py", "benchmarks/quantum/qrf_resource_smoke.qasm", "scripts/generate_quantum_resource_sensitivity.py"), ("tests/test_quantum_microsoft_resource.py",), "fault-tolerant resource estimation and multi-scenario sensitivity envelope"),
    InternalControl("QRF-QRE-GOV", ("worldshepherd_sara/quantum_resource.py",), ("tests/test_quantum_resource.py",), "resource-estimate claims governance"),
    InternalControl("QRF-PQC", ("worldshepherd_sara/pqc_inventory.py", "data/pqc_migration_inventory.json"), ("tests/test_pqc_inventory.py",), "PQC/source crypto discovery and secret-material gate"),
    InternalControl("QRF-OPT", ("worldshepherd_sara/quantum_optimization.py",), ("tests/test_quantum_optimization.py",), "quantum-vs-exact-classical application benchmark"),
    InternalControl("QRF-ROBUST", ("worldshepherd_sara/quantum_robustness.py",), ("tests/test_quantum_robustness.py",), "noise/seed robustness sweeps"),
    InternalControl("QRF-MISSION", ("worldshepherd_sara/quantum_mission_readiness.py",), ("tests/test_quantum_mission_readiness.py",), "97/100 evidence-capped mission gate"),
    InternalControl("QRF-CLOSURE", ("worldshepherd_sara/quantum_closure.py",), ("tests/test_quantum_closure.py",), "per-project closure packages"),
    InternalControl("QRF-EXT-INTAKE", ("worldshepherd_sara/quantum_external_evidence.py",), ("tests/test_quantum_external_evidence.py",), "typed external evidence intake"),
    InternalControl("QRF-EXT-INGEST", ("worldshepherd_sara/quantum_external_ingest.py", "scripts/ingest_quantum_external_evidence.py"), ("tests/test_quantum_external_ingest.py",), "local artifact re-hash, current-gate enforcement, and fail-closed external evidence batch intake"),
    InternalControl("QRF-EXT-REVIEW", ("worldshepherd_sara/quantum_external_review.py", "scripts/generate_quantum_external_review_template.py"), ("tests/test_quantum_external_review.py",), "identified-human technical review bound to the exact ingest decision before any promotion recommendation"),
    InternalControl("QRF-DDIL-CUSTODY", ("worldshepherd_sara/quantum_ddil_evidence.py",), ("tests/test_quantum_ddil_evidence.py",), "DDIL local evidence identity, configuration custody, tamper detection and delayed-provider synchronization without identity regeneration"),
    InternalControl("QRF-QME-PROFILE", ("worldshepherd_sara/quantum_evidence_profile_conformance.py", "scripts/generate_quantum_evidence_profile_conformance.py", "docs/QUANTUM_MISSION_EVIDENCE_PROFILE_DRAFT_2026-08-17.md"), ("tests/test_quantum_evidence_profile_conformance.py",), "ten-case executable conformance suite for the draft vendor-neutral Quantum Mission Evidence Profile"),
    InternalControl("QRF-APNT", ("worldshepherd_sara/quantum_apnt.py", "scripts/generate_quantum_apnt_benchmark.py"), ("tests/test_quantum_apnt.py",), "truth-referenced sensor metrics and synthetic prerequisite"),
    InternalControl("QRF-MATERIALS", ("worldshepherd_sara/quantum_materials.py",), ("tests/test_quantum_materials.py",), "exact-vs-variational materials harness"),
    InternalControl("QRF-ALTI-STRUCTURE", ("worldshepherd_sara/quantum_alti_structure.py", "scripts/generate_quantum_alti_structure_template.py", "docs/QUANTUM_ALTI_STRUCTURE_FREEZE_2026-08-17.md"), ("tests/test_quantum_alti_structure.py",), "fail-closed WS-AlTi physical structure freeze and structure-bound reference-computation gate"),
    InternalControl("QRF-META-CAL", ("worldshepherd_sara/quantum_metasurface_calibration.py", "scripts/generate_quantum_metasurface_calibration_template.py"), ("tests/test_quantum_metasurface_calibration.py",), "fail-closed full-wave versus reduced-order metasurface calibration gate"),
    InternalControl("QRF-LOG-MISSION", ("worldshepherd_sara/quantum_logistics_instance.py", "scripts/generate_quantum_logistics_instance_template.py"), ("tests/test_quantum_logistics_instance.py",), "mission-instance family and full-family classical comparator gate for logistics"),
    InternalControl("QRF-LOG-CP-SAT", ("worldshepherd_sara/quantum_logistics_ortools.py", "scripts/generate_quantum_logistics_classical_baseline.py", "benchmarks/quantum/logistics_cp_sat_fixture.json", "requirements-quantum-logistics.txt", ".github/workflows/quantum-logistics-comparator.yml"), ("tests/test_quantum_logistics_ortools.py",), "optional OR-Tools CP-SAT strong classical comparator with deterministic controlled-fixture evidence and explicit non-mission claims boundary"),
    InternalControl("QRF-EM-METROLOGY", ("worldshepherd_sara/quantum_em_metrology.py", "scripts/generate_quantum_em_metrology_template.py"), ("tests/test_quantum_em_metrology.py",), "bounded calibrated materials/metrology task and null-matrix gate with separate propulsion claim control"),
    InternalControl("QRF-GLOB", ("worldshepherd_sara/quantum_glob_mapping.py",), ("tests/test_quantum_glob_mapping.py",), "formal GLOB quantum mapping admissibility"),
    InternalControl("QRF-EXT-CAMPAIGN", ("worldshepherd_sara/quantum_external_campaign.py", "scripts/generate_quantum_external_campaign.py"), ("tests/test_quantum_external_campaign.py",), "stage-locked external evidence acquisition and no-skip progression"),
    InternalControl("QRF-ACQ-REQUEST", ("worldshepherd_sara/quantum_acquisition_request.py", "scripts/generate_quantum_acquisition_requests.py"), ("tests/test_quantum_acquisition_request.py",), "evidence-complete partner/lab request generation from campaign gates"),
    InternalControl("QRF-CI", (".github/workflows/quantum-readiness.yml", "requirements-quantum.txt"), (), "cross-version CI and retained evidence artifacts"),
)

def audit_internal_closure(root: str | Path) -> dict[str, object]:
    base = Path(root)
    rows = []
    complete = 0
    for control in CONTROLS:
        source_missing = [path for path in control.source_paths if not (base / path).is_file()]
        test_missing = [path for path in control.test_paths if not (base / path).is_file()]
        implemented = not source_missing and not test_missing
        complete += int(implemented)
        rows.append({"control_id": control.control_id, "purpose": control.purpose, "implemented": implemented, "source_paths": list(control.source_paths), "test_paths": list(control.test_paths), "missing": source_missing + test_missing})
    score = round(100.0 * complete / len(CONTROLS), 2)
    return {
        "schema_version": "1.0",
        "metric": "Worldshepherd quantum internally controllable closure completeness",
        "score": score,
        "target": INTERNAL_TARGET,
        "meets_target": score >= INTERNAL_TARGET,
        "controls_total": len(CONTROLS),
        "controls_complete": complete,
        "controls": rows,
        "claim_control": "This score measures implementation presence for internally controllable software/governance/test controls. CI passing is separately required. It is not mission readiness and cannot substitute for QPU, sensor, lab, hardware-in-loop, relevant-environment, or operational evidence.",
    }

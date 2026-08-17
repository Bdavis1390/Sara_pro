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
    InternalControl("QRF-QPU-ADAPTER", ("worldshepherd_sara/quantum_ibm.py", "scripts/run_ibm_qpu_bell.py"), ("tests/test_quantum_ibm.py",), "credential-gated real-QPU path"),
    InternalControl("QRF-QRE", ("worldshepherd_sara/quantum_microsoft_resource.py", "benchmarks/quantum/qrf_resource_smoke.qasm"), ("tests/test_quantum_microsoft_resource.py",), "fault-tolerant resource estimation"),
    InternalControl("QRF-QRE-GOV", ("worldshepherd_sara/quantum_resource.py",), ("tests/test_quantum_resource.py",), "resource-estimate claims governance"),
    InternalControl("QRF-PQC", ("worldshepherd_sara/pqc_inventory.py", "data/pqc_migration_inventory.json"), ("tests/test_pqc_inventory.py",), "PQC/source crypto discovery and secret-material gate"),
    InternalControl("QRF-OPT", ("worldshepherd_sara/quantum_optimization.py",), ("tests/test_quantum_optimization.py",), "quantum-vs-exact-classical application benchmark"),
    InternalControl("QRF-ROBUST", ("worldshepherd_sara/quantum_robustness.py",), ("tests/test_quantum_robustness.py",), "noise/seed robustness sweeps"),
    InternalControl("QRF-MISSION", ("worldshepherd_sara/quantum_mission_readiness.py",), ("tests/test_quantum_mission_readiness.py",), "97/100 evidence-capped mission gate"),
    InternalControl("QRF-CLOSURE", ("worldshepherd_sara/quantum_closure.py",), ("tests/test_quantum_closure.py",), "per-project closure packages"),
    InternalControl("QRF-EXT-INTAKE", ("worldshepherd_sara/quantum_external_evidence.py",), ("tests/test_quantum_external_evidence.py",), "typed external evidence intake"),
    InternalControl("QRF-APNT", ("worldshepherd_sara/quantum_apnt.py",), ("tests/test_quantum_apnt.py",), "truth-referenced sensor metrics"),
    InternalControl("QRF-MATERIALS", ("worldshepherd_sara/quantum_materials.py",), ("tests/test_quantum_materials.py",), "exact-vs-variational materials harness"),
    InternalControl("QRF-GLOB", ("worldshepherd_sara/quantum_glob_mapping.py",), ("tests/test_quantum_glob_mapping.py",), "formal GLOB quantum mapping admissibility"),
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
        rows.append({
            "control_id": control.control_id,
            "purpose": control.purpose,
            "implemented": implemented,
            "source_paths": list(control.source_paths),
            "test_paths": list(control.test_paths),
            "missing": source_missing + test_missing,
        })

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
        "claim_control": (
            "This score measures implementation presence for internally controllable software/governance/test controls. "
            "CI passing is separately required. It is not mission readiness and cannot substitute for QPU, sensor, lab, "
            "hardware-in-loop, relevant-environment, or operational evidence."
        ),
    }

from pathlib import Path

from worldshepherd_sara.quantum_evidence import build_bell_evidence_bundle


def test_bell_evidence_bundle_records_program_software_and_claim_ceiling():
    qasm = Path("benchmarks/quantum/bell_qasm3.qasm")
    bundle = build_bell_evidence_bundle(qasm, shots=1024, seed=9675)

    assert bundle["benchmark_id"] == "QRF-BELL-001"
    assert bundle["program_digest"].startswith("sha256:")
    assert bundle["bundle_digest"].startswith("sha256:")
    assert bundle["execution_class"] == "simulation_only"
    assert bundle["acceptance"]["qpu_gate"] == "not_satisfied"
    assert bundle["runs"]["ideal"]["claim_class"] == "quantum_simulated"
    assert bundle["runs"]["ideal"]["correlated_fraction"] == 1.0
    assert 0.5 < bundle["runs"]["noisy"]["correlated_fraction"] < 1.0
    assert bundle["software"]["qiskit"] != "unknown"
    assert bundle["software"]["qiskit_aer"] != "unknown"

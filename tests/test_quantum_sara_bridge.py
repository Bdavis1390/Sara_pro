import json
from pathlib import Path

from worldshepherd_sara.evidence_registry import EvidenceRegistry, verify_local_raw_digest
from worldshepherd_sara.quantum_evidence import build_bell_evidence_bundle, write_evidence_bundle
from worldshepherd_sara.quantum_sara_bridge import simulation_bundle_to_experiment_record


def test_simulation_bundle_enters_existing_sara_registry(tmp_path):
    bundle = build_bell_evidence_bundle(
        Path("benchmarks/quantum/bell_qasm3.qasm"), shots=1024, seed=9675
    )
    evidence_path = write_evidence_bundle(bundle, tmp_path / "qrf-evidence.json")

    record = simulation_bundle_to_experiment_record(
        bundle,
        evidence_path=evidence_path,
        sara_version="qrf-test",
        commit="test-commit",
    )

    assert record["evidence_class"] == ["SIMULATED", "ARTIFACT"]
    assert record["quantum"]["claim_ceiling"] == "quantum_simulated"
    assert record["quantum"]["hardware_execution"] is False
    assert verify_local_raw_digest(record)["status"] == "VERIFIED"

    registry = EvidenceRegistry(tmp_path / "sara-data")
    envelope = registry.append("experiment", record, actor="QRF_CI")
    assert envelope["record"]["experiment_id"] == record["experiment_id"]

    stored = list((tmp_path / "sara-data" / "evidence" / "experiments.jsonl").read_text(encoding="utf-8").splitlines())
    assert len(stored) == 1
    assert json.loads(stored[0])["record"]["quantum"]["benchmark_id"] == "QRF-BELL-001"

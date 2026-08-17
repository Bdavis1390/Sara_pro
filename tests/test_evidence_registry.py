from __future__ import annotations

import hashlib

import pytest

from worldshepherd_sara.evidence_contract import EvidenceValidationError
from worldshepherd_sara.evidence_registry import (
    DuplicateEvidenceId,
    EvidenceDigestMismatch,
    EvidenceReferenceError,
    EvidenceRegistry,
    EvidenceSupersessionError,
)


def calibration_payload(calibration_id: str = "CAL-UPB-001"):
    return {
        "calibration_id": calibration_id,
        "timestamp_utc": "2026-08-17T14:30:00Z",
        "instrument_id": "WS-UPB-M-001",
        "quantity": "force_x",
        "units": "N",
        "calibration_type": "PRE",
        "method": "reference-force transfer",
        "reference_standard": {
            "standard_id": "REF-FORCE-001",
            "traceability": "declared calibration-chain reference; certificate verification pending",
            "standard_uncertainty": 0.0001,
        },
        "calibration_points": [
            {"applied_value": 0.0, "indicated_value": 0.0},
            {"applied_value": 0.01, "indicated_value": 0.0101},
        ],
        "uncertainty_budget": [
            {"name": "reference", "standard_uncertainty": 0.0003},
            {"name": "repeatability", "standard_uncertainty": 0.0004},
        ],
        "combination_method": "RSS_INDEPENDENT",
        "combined_standard_uncertainty": 0.0005,
        "coverage_factor": 2.0,
        "expanded_uncertainty": 0.001,
        "environment": {"temperature_c": 22.0},
        "raw_data": {"location": "unmounted://calibration/upb001.csv", "digest": "pending"},
        "review_state": "DRAFT",
        "validity": {"campaign_id": "ITX01-CAMPAIGN-A"},
    }


def seed_calibration(registry: EvidenceRegistry):
    registry.append("calibration", calibration_payload(), actor="operator")


def experiment_payload(experiment_id: str = "WS-EXP-001", evidence_class=None):
    return {
        "experiment_id": experiment_id,
        "campaign_id": "ITX01-CAMPAIGN-A",
        "test_article_id": "ITX01-EAD-REF-01",
        "timestamp_utc": "2026-08-17T14:00:00Z",
        "evidence_class": evidence_class or ["MEASURED"],
        "hardware": {
            "geometry_digest": "sha256:geometry-placeholder",
            "configuration_digest": "sha256:configuration-placeholder",
            "material_batch_ids": [],
        },
        "software": {"sara_version": "0.1", "commit": "test-commit"},
        "calibration_ids": ["CAL-UPB-001"],
        "sensor_manifest": [
            {
                "sensor_id": "FORCE-X",
                "quantity": "force_x",
                "units": "N",
                "sample_rate_hz": 1000,
                "calibration_id": "CAL-UPB-001",
            }
        ],
        "environment": {"pressure_pa": 101325},
        "raw_data": {"location": "unmounted://raw/exp001.bin", "digest": "pending"},
        "uncertainty": {"model_id": "UF-001", "expanded_uncertainty": 0.001},
        "hypotheses": {
            "H0": "Measured response is fully explained by known apparatus and EHD effects.",
            "H1": "The configured EHD article produces the predicted thrust within uncertainty.",
        },
        "result_class": "WS-R2",
        "review_state": "DRAFT",
        "glob": {"seed": "99073", "operator": "PA", "orbit_state": "30979", "test_order": 1},
    }


def claim_payload(claim_id: str = "WS-CLAIM-001"):
    return {
        "claim_id": claim_id,
        "statement": "Reference EHD force agrees with the declared model within uncertainty.",
        "claim_class": "ENGINEERING_CONCLUSION",
        "evidence_classes": ["MEASURED", "SIMULATED"],
        "supporting_record_ids": ["WS-EXP-001"],
        "contradicting_record_ids": [],
        "validity_domain": {"test_article": "ITX01-EAD-REF-01"},
        "confidence_status": "SUPPORTED_WITHIN_DOMAIN",
        "review_state": "DRAFT",
        "replication_ids": [],
    }


def test_append_get_and_metrics(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    envelope = registry.append("experiment", experiment_payload(), actor="operator")
    assert envelope["record_id"] == "WS-EXP-001"
    registry.append("claim", claim_payload(), actor="admin")
    metrics = registry.metrics()
    assert metrics["experiments"] == 1
    assert metrics["claims"] == 1
    assert metrics["calibrations"] == 1


def test_measured_experiment_requires_registered_calibration(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    with pytest.raises(EvidenceReferenceError, match="does not exist"):
        registry.append("experiment", experiment_payload(), actor="operator")


def test_sensor_calibration_must_be_declared_by_experiment(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    payload = experiment_payload()
    payload["sensor_manifest"][0]["calibration_id"] = "CAL-OTHER"
    with pytest.raises(EvidenceReferenceError, match="not declared"):
        registry.append("experiment", payload, actor="operator")


def test_duplicate_ids_are_rejected(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    with pytest.raises(DuplicateEvidenceId):
        registry.append("experiment", experiment_payload(), actor="operator")


def test_ids_are_globally_unique_across_record_kinds(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload("WS-SHARED-ID"), actor="operator")
    claim = claim_payload("WS-SHARED-ID")
    claim["supporting_record_ids"] = ["WS-SHARED-ID"]
    with pytest.raises(DuplicateEvidenceId):
        registry.append("claim", claim, actor="admin")


def test_supersession_is_append_only_and_single_successor(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload("WS-EXP-001"), actor="operator")
    registry.append(
        "experiment",
        experiment_payload("WS-EXP-002"),
        actor="operator",
        supersedes_record_id="WS-EXP-001",
    )
    assert registry.get("experiment", "WS-EXP-001")["is_superseded"] is True
    with pytest.raises(EvidenceSupersessionError):
        registry.append(
            "experiment",
            experiment_payload("WS-EXP-003"),
            actor="operator",
            supersedes_record_id="WS-EXP-001",
        )


def test_local_sha256_digest_is_verified(tmp_path):
    raw_path = tmp_path / "raw.bin"
    raw_path.write_bytes(b"worldshepherd-evidence")
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    registry = EvidenceRegistry(tmp_path / "registry")
    seed_calibration(registry)
    payload = experiment_payload()
    payload["raw_data"] = {"location": str(raw_path), "digest": f"sha256:{digest}"}
    envelope = registry.append("experiment", payload, actor="operator")
    assert envelope["digest_verification"]["status"] == "VERIFIED"


def test_local_digest_mismatch_is_rejected(tmp_path):
    raw_path = tmp_path / "raw.bin"
    raw_path.write_bytes(b"worldshepherd-evidence")
    registry = EvidenceRegistry(tmp_path / "registry")
    seed_calibration(registry)
    payload = experiment_payload()
    payload["raw_data"] = {"location": str(raw_path), "digest": "sha256:" + "0" * 64}
    with pytest.raises(EvidenceDigestMismatch):
        registry.append("experiment", payload, actor="operator")


def test_missing_support_reference_is_rejected(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    with pytest.raises(EvidenceReferenceError, match="does not exist"):
        registry.append("claim", claim_payload(), actor="admin")


def test_measured_claim_cannot_be_supported_only_by_simulation(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    registry.append(
        "experiment",
        experiment_payload("WS-EXP-001", evidence_class=["SIMULATED"]),
        actor="operator",
    )
    with pytest.raises(EvidenceReferenceError, match="no supporting record is actually MEASURED"):
        registry.append("claim", claim_payload(), actor="admin")


def test_measured_claim_accepts_actual_measured_support(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    assert registry.append("claim", claim_payload(), actor="admin")["record_id"] == "WS-CLAIM-001"


def test_missing_contradicting_reference_is_rejected(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    claim = claim_payload()
    claim["contradicting_record_ids"] = ["WS-EXP-MISSING"]
    with pytest.raises(EvidenceReferenceError, match="does not exist"):
        registry.append("claim", claim, actor="admin")


def test_unresolved_replication_reference_is_rejected(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    claim = claim_payload()
    claim["claim_class"] = "ANOMALOUS_RESIDUAL"
    claim["confidence_status"] = "INDEPENDENTLY_REPRODUCED"
    claim["replication_ids"] = ["WS-EXP-REPLICATION-MISSING"]
    with pytest.raises(EvidenceReferenceError, match="does not exist"):
        registry.append("claim", claim, actor="admin")


def test_quantitative_measured_claim_requires_uncertainty_reference(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    claim = claim_payload()
    claim["quantitative"] = True
    with pytest.raises(EvidenceValidationError, match="uncertainty_reference"):
        registry.append("claim", claim, actor="admin")


def test_quantitative_measured_claim_accepts_calibration_uncertainty_reference(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    seed_calibration(registry)
    registry.append("experiment", experiment_payload(), actor="operator")
    claim = claim_payload()
    claim["quantitative"] = True
    claim["uncertainty_reference"] = "CAL-UPB-001#expanded_uncertainty"
    envelope = registry.append("claim", claim, actor="admin")
    assert envelope["record"]["uncertainty_reference"] == "CAL-UPB-001#expanded_uncertainty"

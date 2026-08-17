from __future__ import annotations

import pytest

from worldshepherd_sara.evidence_calibration import validate_calibration_record
from worldshepherd_sara.evidence_contract import EvidenceValidationError
from worldshepherd_sara.evidence_registry import EvidenceRegistry


def calibration_payload(calibration_id: str = "CAL-UPB-001"):
    return {
        "calibration_id": calibration_id,
        "timestamp_utc": "2026-08-17T14:30:00Z",
        "instrument_id": "WS-UPB-M-001",
        "quantity": "force_x",
        "units": "N",
        "calibration_type": "PRE",
        "method": "deadweight/reference-force transfer",
        "reference_standard": {
            "standard_id": "REF-FORCE-001",
            "traceability": "declared calibration-chain reference; certificate verification pending",
            "standard_uncertainty": 0.0001,
        },
        "calibration_points": [
            {"applied_value": 0.0, "indicated_value": 0.0},
            {"applied_value": 0.01, "indicated_value": 0.0101},
            {"applied_value": 0.02, "indicated_value": 0.0201},
        ],
        "uncertainty_budget": [
            {"name": "reference", "standard_uncertainty": 0.0003},
            {"name": "repeatability", "standard_uncertainty": 0.0004},
        ],
        "combination_method": "RSS_INDEPENDENT",
        "combined_standard_uncertainty": 0.0005,
        "coverage_factor": 2.0,
        "expanded_uncertainty": 0.001,
        "environment": {"temperature_c": 22.0, "pressure_pa": 101325},
        "raw_data": {"location": "unmounted://calibration/upb001.csv", "digest": "pending"},
        "review_state": "DRAFT",
        "validity": {"campaign_id": "ITX01-CAMPAIGN-A"},
    }


def test_valid_calibration_contract():
    assert validate_calibration_record(calibration_payload())["calibration_id"] == "CAL-UPB-001"


def test_calibration_registry_and_metrics(tmp_path):
    registry = EvidenceRegistry(tmp_path)
    envelope = registry.append("calibration", calibration_payload(), actor="operator")
    assert envelope["record_type"] == "calibration"
    assert envelope["digest_verification"]["status"] == "UNVERIFIED"
    assert registry.get("calibration", "CAL-UPB-001")["record"]["quantity"] == "force_x"
    metrics = registry.metrics()
    assert metrics["calibrations"] == 1
    assert metrics["calibration_types"]["PRE"] == 1


def test_rss_combination_must_be_consistent():
    payload = calibration_payload()
    payload["combined_standard_uncertainty"] = 0.0009
    with pytest.raises(EvidenceValidationError, match="RSS"):
        validate_calibration_record(payload)


def test_expanded_uncertainty_must_match_coverage_factor():
    payload = calibration_payload()
    payload["expanded_uncertainty"] = 0.002
    with pytest.raises(EvidenceValidationError, match="expanded_uncertainty"):
        validate_calibration_record(payload)

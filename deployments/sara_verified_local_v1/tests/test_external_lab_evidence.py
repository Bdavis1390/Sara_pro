from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.external_lab_evidence import (
    ExternalLaboratoryEvidencePackage,
    assess_lab_package,
)

D_A = "sha256:" + "a" * 64
D_B = "sha256:" + "b" * 64
D_C = "sha256:" + "c" * 64


def valid_package(**overrides) -> ExternalLaboratoryEvidencePackage:
    payload = {
        "package_id": "LABPKG-001",
        "campaign_id": "SV-WSALTI-001-P1",
        "project_id": "WS-ALTI",
        "artifact_id": "WS-ALTI-M1-MSZ-PRIME",
        "laboratory_organization": "Example Independent Lab",
        "facility": "Materials Characterization Facility",
        "engagement_reference": "PO-TEST-001",
        "received_at_utc": "2026-09-06T23:40:00Z",
        "acquisition_start_utc": "2026-09-06T20:00:00Z",
        "acquisition_end_utc": "2026-09-06T21:00:00Z",
        "time_reference": "UTC",
        "independence": "external_independence_pending",
        "independence_basis": "External facility generated the measurements; contractual and conflict review remains pending.",
        "samples": [
            {
                "sample_id": "SAMPLE-001",
                "parent_build_id": "BUILD-001",
                "specimen_type": "metallography coupon",
                "orientation": "build-normal",
                "coordinate_or_location": "zone-A",
                "configuration_digest": D_A,
                "custody_events": [
                    {
                        "event_id": "CUST-001",
                        "timestamp_utc": "2026-09-06T19:00:00Z",
                        "actor_or_org": "Worldshepherd",
                        "action": "sample sealed for shipment",
                    },
                    {
                        "event_id": "CUST-002",
                        "timestamp_utc": "2026-09-06T20:00:00Z",
                        "actor_or_org": "Example Independent Lab",
                        "action": "sample received intact",
                    },
                ],
            }
        ],
        "instruments": [
            {
                "instrument_id": "SEM-001",
                "instrument_type": "SEM/EDS",
                "manufacturer": "Example",
                "model": "SEM-X",
                "calibration_record_ids": ["CAL-SEM-001"],
                "calibration_due_or_valid_at_test": True,
            }
        ],
        "methods": [
            {
                "method_id": "M-EDS-001",
                "title": "Local compositional mapping",
                "standard_or_procedure_ref": "LAB-SOP-EDS-01",
                "revision": "1",
            }
        ],
        "files": [
            {
                "file_id": "FILE-RAW-001",
                "role": "raw_data",
                "sha256": D_B,
                "media_type": "application/octet-stream",
                "original_name": "raw-spectrum.dat",
            },
            {
                "file_id": "FILE-CAL-001",
                "role": "calibration",
                "sha256": D_C,
                "media_type": "application/pdf",
                "original_name": "calibration.pdf",
            },
        ],
        "results": [
            {
                "result_id": "R-001",
                "sample_id": "SAMPLE-001",
                "observable": "Sc local concentration",
                "value": 0.15,
                "unit": "mass_percent",
                "uncertainty": "example fixture only",
                "method_id": "M-EDS-001",
                "source_file_ids": ["FILE-RAW-001"],
            }
        ],
    }
    payload.update(overrides)
    return ExternalLaboratoryEvidencePackage(**payload)


def test_complete_package_gets_digest_but_no_maturity_promotion():
    package = valid_package()
    result = assess_lab_package(package)
    assert result["evidence_complete"] is True
    assert result["package_digest"].startswith("sha256:")
    assert len(result["package_digest"]) == 71
    assert result["maturity_promoted"] is False
    assert result["sample_count"] == 1
    assert result["raw_file_count"] == 1


def test_digest_is_deterministic():
    assert valid_package().canonical_digest() == valid_package().canonical_digest()


def test_missing_raw_data_is_blocked():
    package = valid_package(
        files=[
            {
                "file_id": "FILE-CAL-ONLY",
                "role": "calibration",
                "sha256": D_C,
                "media_type": "application/pdf",
            }
        ],
        results=[],
    )
    result = assess_lab_package(package)
    assert result["evidence_complete"] is False
    assert "NO_RAW_DATA_FILES" in result["blockers"]


def test_missing_calibration_reference_is_blocked():
    package = valid_package(
        instruments=[
            {
                "instrument_id": "SEM-NOCAL",
                "instrument_type": "SEM/EDS",
                "calibration_record_ids": [],
                "calibration_due_or_valid_at_test": True,
            }
        ]
    )
    result = assess_lab_package(package)
    assert "MISSING_INSTRUMENT_CALIBRATION_REFS" in result["blockers"]


def test_unknown_result_reference_is_rejected():
    with pytest.raises(ValidationError):
        valid_package(
            results=[
                {
                    "result_id": "R-BAD",
                    "sample_id": "UNKNOWN",
                    "observable": "bad result",
                    "method_id": "M-EDS-001",
                    "source_file_ids": ["FILE-RAW-001"],
                }
            ]
        )

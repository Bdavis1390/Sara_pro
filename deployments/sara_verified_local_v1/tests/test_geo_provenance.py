from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.geo_provenance import (
    BAEGeoEvidenceOverlay,
    ChangeDetectionEvidence,
    EnvironmentalSourceRecord,
    GeoReviewState,
    build_geo_prov_bundle,
)


def test_geo_prov_bundle_preserves_claims_boundary_and_bae_gap_map():
    bundle = build_geo_prov_bundle(
        software_commit="test-commit",
        executed_utc="2026-09-01T15:00:00Z",
        operator="pytest",
    )

    assert bundle["requirement"]["requirement_delta_id"] == "PRE-RD-2026-0020"
    assert bundle["requirement"]["demand_class"] == "EMERGING_DEMAND"
    assert bundle["evidence"][0]["capability_status"] == "SIMULATED_ONLY"
    assert bundle["evidence"][0]["physical_validation_performed"] is False
    assert bundle["geo_provenance"]["change_event"]["null_control_passed"] is True
    assert bundle["bae_evidence_overlay"]["bae_signal_id"] == "PRE-BAE-GEOSPATIAL-PROVENANCE-019"
    assert "independent replay" in bundle["bae_evidence_overlay"]["missing_validation"]
    assert any("No BAE interest" in item for item in bundle["claims_boundary"])
    assert bundle["bundle_digest"].startswith("sha256:")


def test_environmental_source_requires_sha256_retrieval_hash():
    with pytest.raises(ValidationError):
        EnvironmentalSourceRecord(
            source_id="bad-source",
            provider="provider",
            dataset_name="dataset",
            dataset_type="raster",
            dataset_version="v1",
            spatial_resolution="30m",
            temporal_resolution="annual",
            coverage_area="demo",
            license_terms="public",
            retrieval_time_utc="2026-09-01T15:00:00Z",
            retrieval_hash="not-a-hash",
        )


def test_change_detection_requires_hashes_and_human_review_rationale():
    with pytest.raises(ValidationError):
        ChangeDetectionEvidence(
            event_id="event",
            source_id="source",
            baseline_period="t0",
            comparison_period="t1",
            target_geometry="polygon",
            change_type="land-cover",
            area_estimate="1 km2",
            severity_score=0.5,
            confidence_score=0.8,
            uncertainty_reason="bounded uncertainty",
            method="fixture",
            configuration_hash="sha256:abc",
            result_hash="sha256:def",
            null_control_passed=True,
            review_state=GeoReviewState.HUMAN_REVIEW_COMPLETED,
        )


def test_bae_overlay_blocks_false_validation_language():
    with pytest.raises(ValidationError):
        BAEGeoEvidenceOverlay(
            bae_signal_id="bad-overlay",
            maturity_label="BAE_VALIDATED",
            proposed_demo="demo",
            likely_bae_value="value",
        )

import pytest

from external_surrogate import (
    ExternalTraceManifest,
    build_external_surrogate_payload,
    git_blob_sha1,
    parse_pscad_deviation_text,
)
from model import FlexRequest, Verdict
from replay import replay_payload


SAMPLE = "! Time [s] dP_pu\n0.0 -0.010\n0.2 -0.008\n0.4 -0.012\n"


def sample_manifest() -> ExternalTraceManifest:
    return ExternalTraceManifest(
        source_name="unit-test external surrogate",
        source_repository="example/repository",
        source_path="trace.csv",
        source_ref="test",
        source_git_blob_sha1=git_blob_sha1(SAMPLE),
        upstream_dataset_doi="10.0000/example",
        system_base_mw=5000.0,
        data_center_base_mw=250.0,
        claim_status="EXTERNAL PROCESSED SURROGATE / NOT PARTNER VALIDATION",
    )


def request() -> FlexRequest:
    return FlexRequest(
        requested_reduction_mw=10.0,
        response_deadline_s=1.0,
        required_duration_s=0.2,
        max_grid_import_mw=240.0,
    )


def test_git_blob_sha1_matches_known_git_object():
    assert git_blob_sha1("hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_external_parser_maps_per_unit_deviation_to_load():
    points = parse_pscad_deviation_text(SAMPLE, manifest=sample_manifest())
    assert [point.timestamp_s for point in points] == [0.0, 0.2, 0.4]
    assert [point.grid_import_mw for point in points] == pytest.approx(
        [200.0, 210.0, 190.0]
    )
    assert all(not point.meter_provenance_valid for point in points)


def test_external_builder_rejects_source_blob_mismatch():
    manifest = sample_manifest()
    altered = SAMPLE.replace("-0.008", "-0.007")
    with pytest.raises(ValueError, match="external_source_blob_mismatch"):
        build_external_surrogate_payload(altered, request(), manifest=manifest)


def test_external_surrogate_is_fail_closed():
    payload = build_external_surrogate_payload(
        SAMPLE,
        request(),
        manifest=sample_manifest(),
    )
    result = replay_payload(payload)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert {
        "request_provenance_invalid",
        "authorization_evidence_invalid",
        "configuration_custody_invalid",
        "clock_sync_failed",
        "baseline_invalid",
        "meter_provenance_invalid",
    }.issubset(set(result["reasons"]))
    assert "unauthorized_control_action" not in result["reasons"]


def test_external_payload_preserves_source_identity_and_transformation():
    manifest = sample_manifest()
    payload = build_external_surrogate_payload(SAMPLE, request(), manifest=manifest)
    provenance = payload["provenance"]
    assert provenance["source"]["source_git_blob_sha1"] == manifest.source_git_blob_sha1
    assert provenance["source"]["upstream_dataset_doi"] == "10.0000/example"
    assert len(provenance["source_sha256"]) == 64
    assert provenance["evidence_policy"] == "fail_closed_external_surrogate"
    assert "dP_pu" in provenance["transformation"]

import json
from pathlib import Path

import pytest

from model import Verdict
from partner_intake import (
    SCHEMA_VERSION,
    build_partner_intake_payload,
    replay_partner_bundle,
)


def bundle(**overrides):
    value = {
        "schema_version": SCHEMA_VERSION,
        "request": {
            "requested_reduction_mw": 20.0,
            "response_deadline_s": 300.0,
            "required_duration_s": 600.0,
            "max_measured_power_mw": 80.0,
        },
        "baseline_mw": 100.0,
        "partner_context": {
            "source_organization": "Partner Lab",
            "project_or_dataset_id": "event-001",
            "measurement_boundary": "cluster",
            "request_id": "request-001",
            "authorization_record_id": "auth-001",
            "clock_source": "ptp-domain-001",
            "baseline_method": "pre-event mean, 10 min",
            "configuration_id": "cfg-partner-001",
            "meter_id": "meter-partner-001",
            "authorized": True,
            "request_provenance_valid": True,
            "authorization_evidence_valid": True,
            "clocks_synchronized": True,
            "baseline_valid": True,
            "configuration_custody_valid": True,
            "transformation_history": ["none"],
            "limitations": ["cluster-only measurement boundary"],
        },
        "custody": {
            "event_start_utc": "2026-10-01T12:00:00Z",
            "event_end_utc": "2026-10-01T12:12:00Z",
            "timezone": "UTC",
            "baseline_uncertainty_mw": 0.5,
            "transformation_tool": "partner-export",
            "transformation_tool_version": "1.0",
            "redaction_statement": "none",
        },
        "source_objects": [
            {
                "object_id": "cluster-power.csv",
                "role": "primary_measurement",
                "raw_or_derived": "raw",
                "sha256": "a" * 64,
                "media_type": "text/csv",
            }
        ],
        "points": [
            {
                "timestamp_s": 0.0,
                "measured_power_mw": 100.0,
                "telemetry_fresh": True,
                "meter_provenance_valid": True,
                "configuration_id": "cfg-partner-001",
                "meter_id": "meter-partner-001",
            },
            {
                "timestamp_s": 120.0,
                "measured_power_mw": 80.0,
                "workload_pause_mw": 20.0,
                "telemetry_fresh": True,
                "meter_provenance_valid": True,
                "configuration_id": "cfg-partner-001",
                "meter_id": "meter-partner-001",
            },
            {
                "timestamp_s": 420.0,
                "measured_power_mw": 80.0,
                "workload_pause_mw": 20.0,
                "telemetry_fresh": True,
                "meter_provenance_valid": True,
                "configuration_id": "cfg-partner-001",
                "meter_id": "meter-partner-001",
            },
            {
                "timestamp_s": 720.0,
                "measured_power_mw": 80.0,
                "workload_pause_mw": 20.0,
                "telemetry_fresh": True,
                "meter_provenance_valid": True,
                "configuration_id": "cfg-partner-001",
                "meter_id": "meter-partner-001",
            },
        ],
        "auxiliary_evidence": {
            "qos": {
                "latency_ms": 42.0,
                "aggregation_method": "median over event window",
            }
        },
    }
    value.update(overrides)
    return value


def test_complete_partner_bundle_replays_at_declared_scope():
    result = replay_partner_bundle(bundle())
    assert result["verdict"] == Verdict.VERIFIED.value
    assert result["provenance"]["measurement_boundary"] == "cluster"
    assert result["provenance"]["claim_scope"] == "cluster_only"
    assert result["provenance"]["partner_measurement_field"] == "measured_power_mw"
    assert result["provenance"]["internal_trace_field"] == "grid_import_mw"
    assert len(result["provenance"]["partner_manifest_canonical_sha256"]) == 64
    custody = result["provenance"]["partner_custody"]
    assert custody["timezone"] == "UTC"
    assert custody["baseline_uncertainty_mw"] == 0.5
    assert custody["redaction_statement"] == "none"


def test_source_object_and_partner_auxiliary_evidence_are_preserved():
    result = replay_partner_bundle(bundle())
    intake = result["auxiliary_evidence"]["partner_intake"]
    assert intake["schema_version"] == SCHEMA_VERSION
    assert intake["source_objects"][0]["object_id"] == "cluster-power.csv"
    assert intake["source_objects"][0]["sha256"] == "a" * 64
    assert result["auxiliary_evidence"]["partner_supplied"]["qos"]["latency_ms"] == 42.0


def test_external_measurement_name_does_not_promote_cluster_to_grid():
    payload = build_partner_intake_payload(bundle())
    assert payload["points"][0]["grid_import_mw"] == 100.0
    assert payload["provenance"]["measurement_boundary"] == "cluster"
    assert payload["provenance"]["claim_scope"] == "cluster_only"


def test_missing_authorization_record_fails_closed():
    value = bundle()
    value["partner_context"]["authorization_record_id"] = None
    result = replay_partner_bundle(value)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "authorization_evidence_invalid" in result["reasons"]


def test_known_unauthorized_action_is_noncompliant():
    value = bundle()
    value["partner_context"]["authorized"] = False
    result = replay_partner_bundle(value)
    assert result["verdict"] == Verdict.NONCOMPLIANT.value
    assert result["reasons"] == ["unauthorized_control_action"]


def test_validity_flags_must_be_explicit_booleans():
    value = bundle()
    del value["partner_context"]["authorization_evidence_valid"]
    with pytest.raises(ValueError, match="authorization_evidence_valid"):
        build_partner_intake_payload(value)


def test_meter_provenance_must_be_explicit_per_point():
    value = bundle()
    del value["points"][0]["meter_provenance_valid"]
    with pytest.raises(ValueError, match="meter_provenance_valid"):
        build_partner_intake_payload(value)


def test_source_objects_are_required():
    value = bundle(source_objects=[])
    with pytest.raises(ValueError, match="source_objects"):
        build_partner_intake_payload(value)


def test_invalid_source_sha256_is_rejected():
    value = bundle()
    value["source_objects"][0]["sha256"] = "not-a-sha256"
    with pytest.raises(ValueError, match="sha256"):
        build_partner_intake_payload(value)


def test_template_placeholders_are_rejected():
    value = bundle()
    value["partner_context"]["source_organization"] = "replace-with-partner-organization"
    with pytest.raises(ValueError, match="placeholder"):
        build_partner_intake_payload(value)


def test_custody_redaction_placeholder_is_rejected():
    value = bundle()
    value["custody"]["redaction_statement"] = (
        "replace-with-redaction-or-pseudonymization-statement"
    )
    with pytest.raises(ValueError, match="placeholder"):
        build_partner_intake_payload(value)


def test_missing_optional_custody_values_are_preserved_as_unknown():
    value = bundle()
    value["custody"]["event_start_utc"] = None
    value["custody"]["baseline_uncertainty_mw"] = None
    payload = build_partner_intake_payload(value)
    custody = payload["provenance"]["partner_custody"]
    assert custody["event_start_utc"] is None
    assert custody["baseline_uncertainty_mw"] is None


def test_unknown_schema_version_is_rejected():
    value = bundle(schema_version="ws-dcar.partner-event/v9.9")
    with pytest.raises(ValueError, match="schema_version"):
        build_partner_intake_payload(value)


def test_partner_auxiliary_mutation_changes_evidence_hash():
    original = replay_partner_bundle(bundle())
    changed_bundle = bundle()
    changed_bundle["auxiliary_evidence"]["qos"]["latency_ms"] = 43.0
    changed = replay_partner_bundle(changed_bundle)
    assert original["input_sha256"] != changed["input_sha256"]
    assert (
        original["provenance"]["partner_manifest_canonical_sha256"]
        != changed["provenance"]["partner_manifest_canonical_sha256"]
    )


def test_published_schema_matches_runtime_schema_version():
    schema = json.loads(
        Path("partner_event_schema.json").read_text(encoding="utf-8")
    )
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert "max_measured_power_mw" in schema["properties"]["request"]["required"]
    assert "custody" in schema["required"]
    assert "redaction_statement" in schema["properties"]["custody"]["required"]
    point_required = schema["properties"]["points"]["items"]["required"]
    assert "measured_power_mw" in point_required
    assert "meter_provenance_valid" in point_required

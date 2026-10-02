from model import Verdict
from partner_intake import SCHEMA_VERSION, replay_partner_bundle
from partner_preflight import preflight_partner_bundle


def complete_bundle():
    return {
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
        "source_objects": [
            {
                "object_id": "cluster-power.csv",
                "role": "primary_measurement",
                "raw_or_derived": "raw",
                "sha256": "b" * 64,
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
    }


def test_complete_cluster_bundle_is_ready_for_scoped_replay():
    report = preflight_partner_bundle(complete_bundle())
    assert report.replay_ready is True
    assert report.measurement_boundary == "cluster"
    assert report.claim_scope == "cluster_only"
    assert report.blockers == ()
    assert "claim_scope_limited_to_cluster_only" in report.warnings
    assert report.source_object_count == 1
    assert report.point_count == 4
    assert report.source_hashes_declared == 1
    assert len(report.bundle_sha256) == 64


def test_preflight_does_not_replace_verdict():
    value = complete_bundle()
    value["partner_context"]["authorized"] = False
    report = preflight_partner_bundle(value)
    result = replay_partner_bundle(value)
    assert report.replay_ready is True
    assert "action_declared_unauthorized" in report.warnings
    assert result["verdict"] == Verdict.NONCOMPLIANT.value


def test_explicitly_absent_authorization_identifier_is_replayable_evidence_gap():
    value = complete_bundle()
    value["partner_context"]["authorization_record_id"] = None
    report = preflight_partner_bundle(value)
    assert report.replay_ready is True
    assert "authorization_record_id_not_provided" in report.warnings
    result = replay_partner_bundle(value)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "authorization_evidence_invalid" in result["reasons"]


def test_omitted_authorization_field_is_structural_blocker():
    value = complete_bundle()
    del value["partner_context"]["authorization_record_id"]
    report = preflight_partner_bundle(value)
    assert report.replay_ready is False
    assert "authorization_record_id_field_missing" in report.blockers


def test_declared_invalid_evidence_is_warning_not_structural_blocker():
    value = complete_bundle()
    value["partner_context"]["authorization_evidence_valid"] = False
    report = preflight_partner_bundle(value)
    assert report.replay_ready is True
    assert "authorization_evidence_declared_invalid" in report.warnings
    result = replay_partner_bundle(value)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value


def test_template_placeholders_are_preflight_blockers():
    value = complete_bundle()
    value["partner_context"]["configuration_id"] = "replace-with-configuration-id"
    report = preflight_partner_bundle(value)
    assert report.replay_ready is False
    assert "configuration_id_invalid_or_placeholder" in report.blockers


def test_missing_source_hash_is_warning_not_blocker():
    value = complete_bundle()
    value["source_objects"][0]["sha256"] = None
    report = preflight_partner_bundle(value)
    assert report.replay_ready is True
    assert report.source_hashes_declared == 0
    assert "source_object_0_sha256_not_declared" in report.warnings


def test_per_point_missing_provenance_is_blocker():
    value = complete_bundle()
    del value["points"][1]["meter_provenance_valid"]
    report = preflight_partner_bundle(value)
    assert report.replay_ready is False
    assert (
        "point_1_meter_provenance_valid_must_be_explicit_boolean"
        in report.blockers
    )


def test_drift_and_meter_change_are_reported_before_replay():
    value = complete_bundle()
    value["points"][2]["configuration_id"] = "cfg-partner-002"
    value["points"][3]["meter_id"] = "meter-partner-002"
    report = preflight_partner_bundle(value)
    assert report.replay_ready is True
    assert "configuration_drift_present" in report.warnings
    assert "meter_identity_change_present" in report.warnings
    result = replay_partner_bundle(value)
    assert result["verdict"] == Verdict.INSUFFICIENT_EVIDENCE.value
    assert "configuration_custody_invalid" in result["reasons"]
    assert "configuration_drift_detected" in result["reasons"]
    assert "meter_provenance_invalid" in result["reasons"]
    assert "meter_identity_changed" in result["reasons"]


def test_grid_boundary_bundle_has_no_scope_limitation_warning():
    value = complete_bundle()
    value["partner_context"]["measurement_boundary"] = "grid_boundary"
    report = preflight_partner_bundle(value)
    assert report.replay_ready is True
    assert report.claim_scope == "grid_boundary"
    assert all(not item.startswith("claim_scope_limited") for item in report.warnings)


def test_bundle_mutation_changes_preflight_hash():
    original = preflight_partner_bundle(complete_bundle())
    changed = complete_bundle()
    changed["points"][1]["measured_power_mw"] = 79.9
    revised = preflight_partner_bundle(changed)
    assert original.bundle_sha256 != revised.bundle_sha256

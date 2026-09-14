from worldshepherd_sara.lab_interop_g3_readiness import (
    DEFAULT_UNCERTAINTY,
    assess_measurement,
    bench_manifest,
    evaluate_g3_readiness,
    inject_readiness_fault,
    validate_command,
)


def test_manifest_requires_two_devices_and_traceability():
    manifest = bench_manifest()
    assert len({c["device_id"] for c in manifest["channels"]}) == 2
    assert all(c["calibration_id"] for c in manifest["channels"])
    assert all(c["clock_source"] for c in manifest["channels"])
    assert manifest["configuration_digest"].startswith("sha256:")
    assert not any(manifest["claims"].values())


def test_command_envelope_fails_closed():
    assert validate_command(40.0)["decision"] == "ALLOW"
    assert validate_command(90.0)["decision"] == "DENY"
    assert validate_command(40.0, estop_engaged=True)["decision"] == "DENY"


def test_measurement_preserves_raw_normalized_and_uncertainty():
    report = assess_measurement(40.00, normalized_value=40.10)
    assert report["raw_value"] == 40.00
    assert report["normalized_value"] == 40.10
    assert report["uncertainty_rss"] == DEFAULT_UNCERTAINTY.rss
    assert report["normalization_ok"] is True


def test_hard_abort_detects_out_of_bounds_measurement():
    report = assess_measurement(75.0, normalized_value=75.0)
    assert report["hard_abort"] is True


def test_readiness_faults_block_physical_run():
    for name in (
        "expired_calibration",
        "missing_estop",
        "missing_clock",
        "missing_raw_retention",
        "unsafe_default",
    ):
        report = inject_readiness_fault(name)
        assert report["disposition"] == "BLOCK_PHYSICAL_RUN"
        assert report["evidence_digest"].startswith("sha256:")


def test_g3_readiness_is_not_physical_validation():
    report = evaluate_g3_readiness()
    assert report["readiness_gate"] == "G3_READY_FOR_PHYSICAL_BENCH"
    assert report["physical_validation_performed"] is False
    assert report["capability_status"] == "PRE_PHYSICAL_HIL_READINESS"

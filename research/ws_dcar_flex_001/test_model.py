import pytest

from model import FlexObservation, FlexRequest, Verdict, default_scenario, verify_event


def test_reference_event_verifies():
    req, obs = default_scenario()
    result = verify_event(req, obs)
    assert result.verdict is Verdict.VERIFIED
    assert result.measured_reduction_mw == pytest.approx(20.0)
    assert result.decomposed_reduction_mw == pytest.approx(20.0)
    assert result.source_mismatch_mw == pytest.approx(0.0)


@pytest.mark.parametrize(
    "override, reason",
    [
        ({"evidence_complete": False}, "evidence_incomplete"),
        ({"telemetry_fresh": False}, "stale_telemetry"),
        ({"clocks_synchronized": False}, "clock_sync_failed"),
        ({"baseline_valid": False}, "baseline_invalid"),
        ({"meter_provenance_valid": False}, "meter_provenance_invalid"),
        ({"configuration_custody_valid": False}, "configuration_custody_invalid"),
    ],
)
def test_evidence_failures_prevent_verification(override, reason):
    req, obs = default_scenario()
    data = obs.__dict__ | override
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert reason in result.reasons


def test_unauthorized_action_is_noncompliant_even_if_target_met():
    req, obs = default_scenario()
    data = obs.__dict__ | {"authorized": False}
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.NONCOMPLIANT
    assert "unauthorized_control_action" in result.reasons


@pytest.mark.parametrize(
    "override, reason",
    [
        ({"grid_import_mw": 81.0}, "grid_import_limit_exceeded"),
        ({"response_latency_s": 301.0}, "response_deadline_missed"),
        ({"duration_s": 1799.0}, "minimum_duration_not_met"),
    ],
)
def test_operational_contract_failures(override, reason):
    req, obs = default_scenario()
    data = obs.__dict__ | override
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.NONCOMPLIANT
    assert reason in result.reasons


def test_generator_substitution_is_visible_as_exception():
    req, obs = default_scenario()
    data = obs.__dict__ | {
        "hvac_reduction_mw": 0.0,
        "onsite_generation_mw": 3.0,
    }
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.VERIFIED_WITH_EXCEPTIONS
    assert "onsite_generation_substitution" in result.reasons


def test_rebound_is_reported_as_exception():
    req, obs = default_scenario()
    data = obs.__dict__ | {"rebound_energy_mwh": 0.5}
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.VERIFIED_WITH_EXCEPTIONS
    assert "material_rebound_energy" in result.reasons


def test_mechanism_mismatch_is_reported():
    req, obs = default_scenario()
    data = obs.__dict__ | {"battery_discharge_mw": 2.0}
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.VERIFIED_WITH_EXCEPTIONS
    assert "mechanism_decomposition_mismatch" in result.reasons
    assert result.source_mismatch_mw == pytest.approx(3.0)


def test_negative_input_is_insufficient_evidence():
    req, obs = default_scenario()
    data = obs.__dict__ | {"battery_discharge_mw": -1.0}
    result = verify_event(req, FlexObservation(**data))
    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert "invalid_or_negative_numeric_input" in result.reasons


def test_reduction_requirement_is_independent_of_grid_cap():
    req = FlexRequest(
        requested_reduction_mw=25.0,
        response_deadline_s=300.0,
        required_duration_s=1800.0,
        max_grid_import_mw=80.0,
    )
    _, obs = default_scenario()
    result = verify_event(req, obs)
    assert result.verdict is Verdict.NONCOMPLIANT
    assert "requested_reduction_not_met" in result.reasons

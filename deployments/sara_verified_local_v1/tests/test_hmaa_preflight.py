from __future__ import annotations

from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCapturePlan
from worldshepherd_sara.hmaa_preflight import (
    HMAAPreflightRequest,
    HMAAPreflightState,
    PreflightCredentialMode,
    evaluate_preflight,
    verify_preflight_report,
)


ENDPOINT = "https://example.env.sandboxes.developer.anduril.com"


def _static_env():
    return {
        "LATTICE_ENDPOINT": ENDPOINT,
        "ENVIRONMENT_TOKEN": "static-environment-secret",
        "LATTICE_CLIENT_ID": None,
        "LATTICE_CLIENT_SECRET": None,
        "SANDBOXES_TOKEN": "sandbox-authorization-secret",
    }


def _oauth_env():
    return {
        "LATTICE_ENDPOINT": ENDPOINT,
        "ENVIRONMENT_TOKEN": None,
        "LATTICE_CLIENT_ID": "client-001",
        "LATTICE_CLIENT_SECRET": "oauth-client-secret",
        "SANDBOXES_TOKEN": "sandbox-authorization-secret",
    }


def test_default_dry_run_performs_zero_network_and_can_report_missing_external_config():
    report = evaluate_preflight(
        HMAAPreflightRequest(mission_id="PREFLIGHT-001"),
        env={},
    )

    assert report.state is HMAAPreflightState.DRY_RUN_READY
    assert report.network_enabled is False
    assert report.network_call_performed is False
    assert report.credential_mode is PreflightCredentialMode.NONE
    assert report.live_environment_validated is False
    assert report.partner_validated is False
    assert any("LATTICE_ENDPOINT" in item for item in report.blocking_reasons)
    assert verify_preflight_report(report) is True


def test_static_token_configuration_can_be_authorized_read_ready_only_with_explicit_opt_in():
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-STATIC",
            network_enabled=True,
            authorization_confirmed=True,
        ),
        env=_static_env(),
    )

    assert report.state is HMAAPreflightState.AUTHORIZED_READ_READY
    assert report.credential_mode is PreflightCredentialMode.STATIC_ENVIRONMENT_TOKEN
    assert report.network_call_performed is False
    assert report.endpoint == ENDPOINT
    assert all(report.credential_presence[name] is True for name in ["LATTICE_ENDPOINT", "ENVIRONMENT_TOKEN", "SANDBOXES_TOKEN"])
    assert report.flight_validated is False
    assert verify_preflight_report(report) is True


def test_oauth_configuration_can_be_authorized_read_ready_without_acquiring_token():
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-OAUTH",
            network_enabled=True,
            authorization_confirmed=True,
        ),
        env=_oauth_env(),
    )

    assert report.state is HMAAPreflightState.AUTHORIZED_READ_READY
    assert report.credential_mode is PreflightCredentialMode.OAUTH_CLIENT_CREDENTIALS
    assert report.network_call_performed is False
    assert report.credential_presence["ENVIRONMENT_TOKEN"] is False
    assert report.credential_presence["LATTICE_CLIENT_SECRET"] is True


def test_network_enabled_without_explicit_authorization_is_blocked():
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-NO-AUTH",
            network_enabled=True,
            authorization_confirmed=False,
        ),
        env=_oauth_env(),
    )

    assert report.state is HMAAPreflightState.BLOCKED
    assert report.network_call_performed is False
    assert any("explicit authorization" in item for item in report.blocking_reasons)


def test_ambiguous_static_and_oauth_modes_are_blocked_for_network_readiness():
    env = _oauth_env()
    env["ENVIRONMENT_TOKEN"] = "also-static"
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-AMBIGUOUS",
            network_enabled=True,
            authorization_confirmed=True,
        ),
        env=env,
    )

    assert report.state is HMAAPreflightState.BLOCKED
    assert report.credential_mode is PreflightCredentialMode.AMBIGUOUS
    assert any("both configured" in item for item in report.blocking_reasons)


def test_incomplete_oauth_mode_is_blocked():
    env = _oauth_env()
    env["LATTICE_CLIENT_SECRET"] = None
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-INCOMPLETE",
            network_enabled=True,
            authorization_confirmed=True,
        ),
        env=env,
    )

    assert report.state is HMAAPreflightState.BLOCKED
    assert report.credential_mode is PreflightCredentialMode.INCOMPLETE


def test_invalid_endpoint_never_becomes_authorized_read_ready():
    env = _static_env()
    env["LATTICE_ENDPOINT"] = "https://example.invalid"
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-BAD-ENDPOINT",
            network_enabled=True,
            authorization_confirmed=True,
        ),
        env=env,
    )

    assert report.state is HMAAPreflightState.BLOCKED
    assert report.endpoint_valid is False
    assert report.endpoint is None


def test_zero_message_capture_plan_is_blocked_even_in_dry_run():
    report = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id="PREFLIGHT-ZERO",
            capture_plan=SandboxReadCapturePlan(
                max_entity_messages=0,
                max_task_messages=0,
            ),
        ),
        env=_static_env(),
    )

    assert report.state is HMAAPreflightState.BLOCKED
    assert report.dry_run_checks["finite_capture_plan_valid"] is False


def test_report_contains_credential_presence_only_not_secret_values():
    env = _oauth_env()
    report = evaluate_preflight(
        HMAAPreflightRequest(mission_id="PREFLIGHT-REDACTION"),
        env=env,
    )
    encoded = report.model_dump_json()

    assert "oauth-client-secret" not in encoded
    assert "sandbox-authorization-secret" not in encoded
    assert "client-001" not in encoded
    assert report.credential_presence["LATTICE_CLIENT_ID"] is True
    assert report.credential_presence["LATTICE_CLIENT_SECRET"] is True


def test_preflight_hash_detects_tampering():
    report = evaluate_preflight(
        HMAAPreflightRequest(mission_id="PREFLIGHT-HASH"),
        env=_static_env(),
    )
    tampered = report.model_copy(update={"mission_id": "TAMPERED"})

    assert verify_preflight_report(report) is True
    assert verify_preflight_report(tampered) is False


def test_dry_run_never_promotes_any_validation_flag_even_when_fully_configured():
    report = evaluate_preflight(
        HMAAPreflightRequest(mission_id="PREFLIGHT-NO-PROMOTION"),
        env=_oauth_env(),
    )

    assert report.state is HMAAPreflightState.DRY_RUN_READY
    assert report.live_environment_validated is False
    assert report.partner_validated is False
    assert report.flight_validated is False
    assert report.operationally_validated is False
    assert report.dry_run_checks["no_validation_state_promotion"] is True

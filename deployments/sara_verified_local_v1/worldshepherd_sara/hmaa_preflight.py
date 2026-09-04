from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, Field, SecretStr, ValidationError

from .hmaa_lattice_capture import SandboxReadCapturePlan
from .hmaa_lattice_contract import (
    validate_entity_stream_request,
    validate_task_stream_request,
)
from .hmaa_lattice_sandbox import ALLOWED_READ_STREAM_PATHS, SandboxReadConfig


HMAA_PREFLIGHT_VERSION = "worldshepherd.hmaa.preflight.v1.1"


class PreflightCredentialMode(str, Enum):
    NONE = "NONE"
    STATIC_ENVIRONMENT_TOKEN = "STATIC_ENVIRONMENT_TOKEN"
    OAUTH_CLIENT_CREDENTIALS = "OAUTH_CLIENT_CREDENTIALS"
    AMBIGUOUS = "AMBIGUOUS"
    INCOMPLETE = "INCOMPLETE"


class HMAAPreflightState(str, Enum):
    DRY_RUN_READY = "DRY_RUN_READY"
    AUTHORIZED_READ_READY = "AUTHORIZED_READ_READY"
    BLOCKED = "BLOCKED"


class HMAAPreflightRequest(BaseModel):
    mission_id: str = Field(min_length=1, max_length=512)
    network_enabled: bool = False
    authorization_confirmed: bool = False
    capture_plan: SandboxReadCapturePlan = Field(default_factory=SandboxReadCapturePlan)


class HMAAPreflightReport(BaseModel):
    report_version: str = HMAA_PREFLIGHT_VERSION
    state: HMAAPreflightState
    mission_id: str
    network_enabled: bool
    authorization_confirmed: bool
    network_call_performed: bool = False
    credential_mode: PreflightCredentialMode
    endpoint: str | None = None
    endpoint_valid: bool = False
    credential_presence: dict[str, bool]
    allowed_paths: list[str]
    capture_plan: dict[str, Any]
    dry_run_checks: dict[str, bool]
    blocking_reasons: list[str] = Field(default_factory=list)
    live_environment_validated: bool = False
    partner_validated: bool = False
    flight_validated: bool = False
    operationally_validated: bool = False
    report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _present(env: Mapping[str, str | None], name: str) -> bool:
    value = env.get(name)
    return isinstance(value, str) and bool(value.strip())


def _credential_mode(presence: Mapping[str, bool]) -> PreflightCredentialMode:
    static = bool(presence["ENVIRONMENT_TOKEN"])
    oauth_id = bool(presence["LATTICE_CLIENT_ID"])
    oauth_secret = bool(presence["LATTICE_CLIENT_SECRET"])
    oauth_any = oauth_id or oauth_secret
    oauth_complete = oauth_id and oauth_secret

    if static and oauth_any:
        return PreflightCredentialMode.AMBIGUOUS
    if static:
        return PreflightCredentialMode.STATIC_ENVIRONMENT_TOKEN
    if oauth_complete:
        return PreflightCredentialMode.OAUTH_CLIENT_CREDENTIALS
    if oauth_any:
        return PreflightCredentialMode.INCOMPLETE
    return PreflightCredentialMode.NONE


def _validate_endpoint_without_secrets(endpoint: str | None) -> tuple[str | None, bool, str | None]:
    if not endpoint or not endpoint.strip():
        return None, False, "LATTICE_ENDPOINT is missing"
    try:
        validated = SandboxReadConfig(
            endpoint=endpoint,
            environment_token=None,
            sandboxes_token=SecretStr("preflight-presence-only"),
        )
    except ValidationError:
        return None, False, "LATTICE_ENDPOINT failed Sandbox endpoint validation"
    return validated.endpoint, True, None


def _validated_plan(plan: SandboxReadCapturePlan) -> tuple[dict[str, Any], bool, str | None]:
    if plan.max_entity_messages == 0 and plan.max_task_messages == 0:
        return {}, False, "capture plan must request at least one finite stream message"
    try:
        entity_request = validate_entity_stream_request(plan.entity_request)
        task_request = validate_task_stream_request(plan.task_request)
    except (TypeError, ValueError) as exc:
        return {}, False, f"capture plan contract validation failed: {type(exc).__name__}"
    return {
        "entity_request": entity_request,
        "task_request": task_request,
        "max_entity_messages": plan.max_entity_messages,
        "max_task_messages": plan.max_task_messages,
    }, True, None


def evaluate_preflight(
    request: HMAAPreflightRequest,
    *,
    env: Mapping[str, str | None],
) -> HMAAPreflightReport:
    """Evaluate HMAA read-only readiness without performing any network call."""

    names = (
        "LATTICE_ENDPOINT",
        "ENVIRONMENT_TOKEN",
        "LATTICE_CLIENT_ID",
        "LATTICE_CLIENT_SECRET",
        "SANDBOXES_TOKEN",
    )
    presence = {name: _present(env, name) for name in names}
    mode = _credential_mode(presence)

    endpoint, endpoint_valid, endpoint_error = _validate_endpoint_without_secrets(
        env.get("LATTICE_ENDPOINT")
    )
    plan_body, plan_valid, plan_error = _validated_plan(request.capture_plan)

    blockers: list[str] = []
    if endpoint_error:
        blockers.append(endpoint_error)
    if plan_error:
        blockers.append(plan_error)
    if not presence["SANDBOXES_TOKEN"]:
        blockers.append("SANDBOXES_TOKEN is missing")
    if mode is PreflightCredentialMode.NONE:
        blockers.append("no environment-token credential mode is configured")
    elif mode is PreflightCredentialMode.INCOMPLETE:
        blockers.append("OAuth client-credential configuration is incomplete")
    elif mode is PreflightCredentialMode.AMBIGUOUS:
        blockers.append("static and OAuth environment-token modes are both configured")

    external_config_ready = (
        endpoint_valid
        and plan_valid
        and presence["SANDBOXES_TOKEN"]
        and mode
        in {
            PreflightCredentialMode.STATIC_ENVIRONMENT_TOKEN,
            PreflightCredentialMode.OAUTH_CLIENT_CREDENTIALS,
        }
    )

    if request.network_enabled:
        if not request.authorization_confirmed:
            blockers.append(
                "network-enabled readiness requires explicit authorization confirmation"
            )
        state = (
            HMAAPreflightState.AUTHORIZED_READ_READY
            if external_config_ready and request.authorization_confirmed
            else HMAAPreflightState.BLOCKED
        )
    else:
        # Dry-run evaluation is useful even when external credentials are absent.
        state = HMAAPreflightState.DRY_RUN_READY if plan_valid else HMAAPreflightState.BLOCKED

    dry_run_checks = {
        "zero_network_calls": True,
        "endpoint_contract_valid": endpoint_valid,
        "finite_capture_plan_valid": plan_valid,
        "sandbox_authorization_token_present": presence["SANDBOXES_TOKEN"],
        "single_environment_credential_mode": mode
        in {
            PreflightCredentialMode.STATIC_ENVIRONMENT_TOKEN,
            PreflightCredentialMode.OAUTH_CLIENT_CREDENTIALS,
        },
        "explicit_authorization_if_network_enabled": (
            not request.network_enabled or request.authorization_confirmed
        ),
        "read_only_paths_only": True,
        "no_validation_state_promotion": True,
    }

    body = {
        "report_version": HMAA_PREFLIGHT_VERSION,
        "state": state.value,
        "mission_id": request.mission_id,
        "network_enabled": request.network_enabled,
        "authorization_confirmed": request.authorization_confirmed,
        "network_call_performed": False,
        "credential_mode": mode.value,
        "endpoint": endpoint,
        "endpoint_valid": endpoint_valid,
        "credential_presence": presence,
        "allowed_paths": sorted(ALLOWED_READ_STREAM_PATHS),
        "capture_plan": plan_body,
        "dry_run_checks": dry_run_checks,
        "blocking_reasons": blockers,
        "live_environment_validated": False,
        "partner_validated": False,
        "flight_validated": False,
        "operationally_validated": False,
    }
    return HMAAPreflightReport(
        **body,
        report_sha256=_sha256_json(body),
    )


def verify_preflight_report(report: HMAAPreflightReport) -> bool:
    body = report.model_dump(mode="json", exclude={"report_sha256"})
    return _sha256_json(body) == report.report_sha256

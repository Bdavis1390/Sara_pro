from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr

from .hmaa_attestation import HMAAAttestationReport, HMAAAttestationState, attest_candidate_captures
from .hmaa_lattice_capture import (
    SandboxReadCapturePlan,
    SandboxReadCaptureResult,
    capture_readonly_stream_evidence,
)
from .hmaa_lattice_contract import LatticeReadTransport
from .hmaa_lattice_oauth import SandboxClientCredentialsTokenProvider, SandboxOAuthConfig
from .hmaa_lattice_sandbox import SandboxReadConfig, SandboxReadOnlySSETransport
from .hmaa_partner_package import HMAAPartnerValidationRequest, build_partner_validation_request
from .hmaa_preflight import (
    HMAAPreflightReport,
    HMAAPreflightRequest,
    HMAAPreflightState,
    PreflightCredentialMode,
    evaluate_preflight,
    verify_preflight_report,
)
from .hmaa_session_partner import (
    HMAASessionPartnerValidationRequest,
    build_session_partner_validation_request,
    canonical_session_partner_request_bytes,
)


HMAA_AUTHORIZED_SESSION_VERSION = "worldshepherd.hmaa.authorized-read-session.v1.2"
HMAA_SESSION_ARTIFACT_MANIFEST_VERSION = "worldshepherd.hmaa.authorized-read-session-artifacts.v1.2"


class HMAAAuthorizedReadSessionStatus(str, Enum):
    CANDIDATE_EVIDENCE_CAPTURED = "CANDIDATE_EVIDENCE_CAPTURED"
    READY_FOR_PARTNER_VALIDATION_REQUEST = "READY_FOR_PARTNER_VALIDATION_REQUEST"


class HMAAAuthorizedReadSessionRequest(BaseModel):
    mission_id: str = Field(min_length=1, max_length=512)
    authorization_confirmed: bool = False
    capture_plan: SandboxReadCapturePlan = Field(default_factory=SandboxReadCapturePlan)
    capture_attempts: int = Field(default=3, ge=1, le=10)


class HMAAAuthorizedReadSessionReceipt(BaseModel):
    session_version: str = HMAA_AUTHORIZED_SESSION_VERSION
    status: HMAAAuthorizedReadSessionStatus
    mission_id: str
    endpoint: str
    credential_mode: PreflightCredentialMode
    preflight_report_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    network_call_performed: bool = True
    allowed_paths: list[str]
    capture_attempt_count: int = Field(ge=1)
    distinct_capture_count: int = Field(ge=1)
    capture_sha256: list[str]
    attestation_state: HMAAAttestationState
    attestation_aggregate_sha256: str | None = None
    partner_request_package_sha256: str | None = None
    external_environment_provenance_confirmed: bool = False
    live_environment_validated: bool = False
    partner_validated: bool = False
    flight_validated: bool = False
    operationally_validated: bool = False
    claimable_labels: list[str]
    prohibited_claims: list[str]
    receipt_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class HMAAAuthorizedReadSessionRun(BaseModel):
    preflight: HMAAPreflightReport
    captures: list[SandboxReadCaptureResult]
    attestation: HMAAAttestationReport
    partner_validation_request: HMAAPartnerValidationRequest | None = None
    partner_validation_envelope: HMAASessionPartnerValidationRequest | None = None
    receipt: HMAAAuthorizedReadSessionReceipt


class HMAASessionArtifactManifest(BaseModel):
    manifest_version: str = HMAA_SESSION_ARTIFACT_MANIFEST_VERSION
    mission_id: str
    session_receipt_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    partner_exchange_package_sha256: str | None = None
    files: dict[str, str]
    local_capture_payloads_included: bool = True
    partner_package_excludes_raw_capture_payloads: bool = True
    live_environment_validated: bool = False
    package_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


TransportFactory = Callable[
    [HMAAPreflightReport, Mapping[str, str | None]],
    LatticeReadTransport,
]


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _require_env_value(env: Mapping[str, str | None], name: str) -> str:
    value = env.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"authorized read session requires {name}")
    return value.strip()


def build_readonly_transport_from_preflight(
    report: HMAAPreflightReport,
    env: Mapping[str, str | None],
) -> LatticeReadTransport:
    """Build only the bounded read-only Sandbox transport after verified preflight."""

    if report.state is not HMAAPreflightState.AUTHORIZED_READ_READY:
        raise ValueError("read transport requires AUTHORIZED_READ_READY preflight")
    if not verify_preflight_report(report):
        raise ValueError("preflight report digest verification failed")
    if report.network_call_performed:
        raise ValueError("preflight must remain a zero-network record")
    if report.endpoint is None:
        raise ValueError("authorized preflight is missing a validated endpoint")

    sandboxes_token = SecretStr(_require_env_value(env, "SANDBOXES_TOKEN"))

    if report.credential_mode is PreflightCredentialMode.STATIC_ENVIRONMENT_TOKEN:
        read_config = SandboxReadConfig(
            endpoint=report.endpoint,
            environment_token=SecretStr(_require_env_value(env, "ENVIRONMENT_TOKEN")),
            sandboxes_token=sandboxes_token,
        )
        return SandboxReadOnlySSETransport(read_config)

    if report.credential_mode is PreflightCredentialMode.OAUTH_CLIENT_CREDENTIALS:
        oauth_config = SandboxOAuthConfig(
            endpoint=report.endpoint,
            client_id=_require_env_value(env, "LATTICE_CLIENT_ID"),
            client_secret=SecretStr(_require_env_value(env, "LATTICE_CLIENT_SECRET")),
            sandboxes_token=sandboxes_token,
        )
        token_provider = SandboxClientCredentialsTokenProvider(oauth_config)
        read_config = SandboxReadConfig(
            endpoint=report.endpoint,
            environment_token=None,
            sandboxes_token=sandboxes_token,
        )
        return SandboxReadOnlySSETransport(
            read_config,
            environment_token_provider=token_provider,
        )

    raise ValueError("authorized preflight has unsupported credential mode")


def _build_receipt(
    *,
    preflight: HMAAPreflightReport,
    captures: list[SandboxReadCaptureResult],
    attestation: HMAAAttestationReport,
    partner_request: HMAAPartnerValidationRequest | None,
) -> HMAAAuthorizedReadSessionReceipt:
    if preflight.endpoint is None:
        raise ValueError("session receipt requires a validated endpoint")
    if not captures:
        raise ValueError("session receipt requires capture evidence")
    if attestation.mission_id != preflight.mission_id:
        raise ValueError("preflight and attestation mission IDs do not match")
    if attestation.live_environment_validated:
        raise ValueError("session receipt cannot inherit a live-validation claim")

    status = (
        HMAAAuthorizedReadSessionStatus.READY_FOR_PARTNER_VALIDATION_REQUEST
        if partner_request is not None
        else HMAAAuthorizedReadSessionStatus.CANDIDATE_EVIDENCE_CAPTURED
    )
    capture_hashes = [capture.capture_sha256 for capture in attestation.captures]
    body = {
        "session_version": HMAA_AUTHORIZED_SESSION_VERSION,
        "status": status.value,
        "mission_id": preflight.mission_id,
        "endpoint": preflight.endpoint,
        "credential_mode": preflight.credential_mode.value,
        "preflight_report_sha256": preflight.report_sha256,
        "network_call_performed": True,
        "allowed_paths": list(preflight.allowed_paths),
        "capture_attempt_count": len(captures),
        "distinct_capture_count": attestation.distinct_capture_count,
        "capture_sha256": capture_hashes,
        "attestation_state": attestation.state.value,
        "attestation_aggregate_sha256": attestation.aggregate_sha256,
        "partner_request_package_sha256": (
            partner_request.package_sha256 if partner_request is not None else None
        ),
        "external_environment_provenance_confirmed": False,
        "live_environment_validated": False,
        "partner_validated": False,
        "flight_validated": False,
        "operationally_validated": False,
        "claimable_labels": [
            "IMPLEMENTED IN SOFTWARE",
            "REQUIRES PARTNER VALIDATION",
        ],
        "prohibited_claims": [
            "LIVE_ENVIRONMENT_VALIDATED",
            "PARTNER_VALIDATED",
            "FLIGHT_VALIDATED",
            "OPERATIONALLY_VALIDATED",
        ],
    }
    return HMAAAuthorizedReadSessionReceipt(
        **body,
        receipt_sha256=_sha256_json(body),
    )


def verify_authorized_read_session_receipt(
    receipt: HMAAAuthorizedReadSessionReceipt,
) -> bool:
    body = receipt.model_dump(mode="json", exclude={"receipt_sha256"})
    return _sha256_json(body) == receipt.receipt_sha256


def run_authorized_read_session(
    request: HMAAAuthorizedReadSessionRequest,
    *,
    env: Mapping[str, str | None],
    transport_factory: TransportFactory | None = None,
) -> HMAAAuthorizedReadSessionRun:
    """Run a finite authorized read-only Sandbox evidence session.

    This function is intentionally impossible to use as a dry-run. It requires
    explicit authorization confirmation, a valid network-enabled preflight, and
    a transport restricted by the existing Lattice read-only protocol. It does
    not promote candidate capture evidence into a live/partner/operational claim.
    """

    preflight = evaluate_preflight(
        HMAAPreflightRequest(
            mission_id=request.mission_id,
            network_enabled=True,
            authorization_confirmed=request.authorization_confirmed,
            capture_plan=request.capture_plan,
        ),
        env=env,
    )
    if preflight.state is not HMAAPreflightState.AUTHORIZED_READ_READY:
        reasons = "; ".join(preflight.blocking_reasons) or "preflight blocked"
        raise ValueError(f"authorized read session blocked: {reasons}")
    if not verify_preflight_report(preflight):
        raise ValueError("authorized read session preflight digest verification failed")

    factory = transport_factory or build_readonly_transport_from_preflight
    transport = factory(preflight, env)
    if not isinstance(transport, LatticeReadTransport):
        raise TypeError("transport factory did not return a LatticeReadTransport")

    captures = [
        capture_readonly_stream_evidence(
            transport=transport,
            mission_id=request.mission_id,
            plan=request.capture_plan,
        )
        for _ in range(request.capture_attempts)
    ]
    attestation = attest_candidate_captures(captures)
    partner_request = None
    if attestation.state is HMAAAttestationState.EXTERNAL_ATTESTATION_REQUIRED:
        partner_request = build_partner_validation_request(attestation)

    receipt = _build_receipt(
        preflight=preflight,
        captures=captures,
        attestation=attestation,
        partner_request=partner_request,
    )
    partner_envelope = (
        build_session_partner_validation_request(receipt, partner_request)
        if partner_request is not None
        else None
    )
    return HMAAAuthorizedReadSessionRun(
        preflight=preflight,
        captures=captures,
        attestation=attestation,
        partner_validation_request=partner_request,
        partner_validation_envelope=partner_envelope,
        receipt=receipt,
    )


def export_authorized_read_session(
    run: HMAAAuthorizedReadSessionRun,
    output_dir: Path,
) -> HMAASessionArtifactManifest:
    """Write local evidence artifacts and a hash-bound manifest.

    Capture JSON is local review evidence and may contain simulated environment
    payloads. The session partner request is the secret-free, raw-payload-
    excluding external exchange artifact and cryptographically binds the named
    endpoint, preflight, session receipt, and inner v0.8 evidence request.
    """

    if not verify_preflight_report(run.preflight):
        raise ValueError("cannot export session with invalid preflight digest")
    if not verify_authorized_read_session_receipt(run.receipt):
        raise ValueError("cannot export session with invalid receipt digest")
    if run.partner_validation_envelope is not None:
        canonical_session_partner_request_bytes(run.partner_validation_envelope)

    output_dir.mkdir(parents=True, exist_ok=False)
    serializable: dict[str, Any] = {
        "preflight-report.json": run.preflight.model_dump(mode="json"),
        "attestation-report.json": run.attestation.model_dump(mode="json"),
        "session-receipt.json": run.receipt.model_dump(mode="json"),
    }
    for index, capture in enumerate(run.captures, start=1):
        serializable[f"local-capture-{index:02d}.json"] = capture.model_dump(mode="json")
    if run.partner_validation_request is not None:
        serializable["partner-validation-request-v0.8.json"] = (
            run.partner_validation_request.model_dump(mode="json")
        )
    if run.partner_validation_envelope is not None:
        serializable["partner-session-validation-request-v1.2.json"] = (
            run.partner_validation_envelope.model_dump(mode="json")
        )

    file_hashes: dict[str, str] = {}
    for name, value in sorted(serializable.items()):
        raw = (
            json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        (output_dir / name).write_bytes(raw)
        file_hashes[name] = _sha256_bytes(raw)

    body = {
        "manifest_version": HMAA_SESSION_ARTIFACT_MANIFEST_VERSION,
        "mission_id": run.receipt.mission_id,
        "session_receipt_sha256": run.receipt.receipt_sha256,
        "partner_exchange_package_sha256": (
            run.partner_validation_envelope.package_sha256
            if run.partner_validation_envelope is not None
            else None
        ),
        "files": dict(sorted(file_hashes.items())),
        "local_capture_payloads_included": True,
        "partner_package_excludes_raw_capture_payloads": True,
        "live_environment_validated": False,
    }
    manifest = HMAASessionArtifactManifest(
        **body,
        package_sha256=_sha256_json(body),
    )
    manifest_raw = (
        json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    (output_dir / "manifest.json").write_bytes(manifest_raw)
    return manifest


def verify_session_artifact_manifest(
    manifest: HMAASessionArtifactManifest,
    output_dir: Path,
) -> bool:
    body = manifest.model_dump(mode="json", exclude={"package_sha256"})
    if _sha256_json(body) != manifest.package_sha256:
        return False
    for name, expected in manifest.files.items():
        path = output_dir / name
        if not path.is_file() or _sha256_bytes(path.read_bytes()) != expected:
            return False
    return True

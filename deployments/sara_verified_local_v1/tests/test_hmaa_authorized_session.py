from __future__ import annotations

import json

import pytest

from worldshepherd_sara.hmaa_authorized_session import (
    HMAAAuthorizedReadSessionRequest,
    HMAAAuthorizedReadSessionStatus,
    export_authorized_read_session,
    run_authorized_read_session,
    verify_authorized_read_session_receipt,
    verify_session_artifact_manifest,
)
from worldshepherd_sara.hmaa_attestation import HMAAAttestationState
from worldshepherd_sara.hmaa_lattice_capture import SandboxReadCapturePlan


ENDPOINT = "https://session-test.env.sandboxes.developer.anduril.com"


def _oauth_env():
    return {
        "LATTICE_ENDPOINT": ENDPOINT,
        "ENVIRONMENT_TOKEN": None,
        "LATTICE_CLIENT_ID": "session-client-id",
        "LATTICE_CLIENT_SECRET": "session-client-secret-do-not-leak",
        "SANDBOXES_TOKEN": "session-sandbox-token-do-not-leak",
    }


class DistinctHeartbeatTransport:
    def __init__(self) -> None:
        self.calls = 0

    def stream_entities(self, request):
        self.calls += 1
        second = self.calls
        yield {
            "heartbeat": {
                "timestamp": f"2026-09-14T19:00:0{second}Z",
                "sequence": second,
            }
        }

    def stream_tasks(self, request):
        if False:
            yield {}


class DuplicateHeartbeatTransport:
    def stream_entities(self, request):
        yield {
            "heartbeat": {
                "timestamp": "2026-09-14T19:00:01Z",
                "sequence": 1,
            }
        }

    def stream_tasks(self, request):
        if False:
            yield {}


def _request(*, authorized: bool = True, attempts: int = 3):
    return HMAAAuthorizedReadSessionRequest(
        mission_id="HMAA-AUTHORIZED-SESSION-001",
        authorization_confirmed=authorized,
        capture_attempts=attempts,
        capture_plan=SandboxReadCapturePlan(
            max_entity_messages=1,
            max_task_messages=0,
        ),
    )


def test_three_distinct_authorized_captures_produce_partner_request_not_live_claim():
    transport = DistinctHeartbeatTransport()
    run = run_authorized_read_session(
        _request(),
        env=_oauth_env(),
        transport_factory=lambda report, env: transport,
    )

    assert run.preflight.network_call_performed is False
    assert run.preflight.authorization_confirmed is True
    assert run.receipt.network_call_performed is True
    assert run.receipt.endpoint == ENDPOINT
    assert run.receipt.status is HMAAAuthorizedReadSessionStatus.READY_FOR_PARTNER_VALIDATION_REQUEST
    assert run.attestation.state is HMAAAttestationState.EXTERNAL_ATTESTATION_REQUIRED
    assert run.attestation.distinct_capture_count == 3
    assert run.partner_validation_request is not None
    assert run.receipt.partner_request_package_sha256 == run.partner_validation_request.package_sha256
    assert run.receipt.external_environment_provenance_confirmed is False
    assert run.receipt.live_environment_validated is False
    assert run.receipt.partner_validated is False
    assert run.receipt.operationally_validated is False
    assert verify_authorized_read_session_receipt(run.receipt) is True

    encoded = run.model_dump_json()
    assert "session-client-secret-do-not-leak" not in encoded
    assert "session-sandbox-token-do-not-leak" not in encoded
    assert "session-client-id" not in encoded


def test_duplicate_captures_remain_candidate_only():
    run = run_authorized_read_session(
        _request(),
        env=_oauth_env(),
        transport_factory=lambda report, env: DuplicateHeartbeatTransport(),
    )

    assert run.attestation.state is HMAAAttestationState.CANDIDATE_EVIDENCE
    assert run.attestation.capture_count == 3
    assert run.attestation.distinct_capture_count == 1
    assert run.partner_validation_request is None
    assert run.receipt.status is HMAAAuthorizedReadSessionStatus.CANDIDATE_EVIDENCE_CAPTURED
    assert run.receipt.partner_request_package_sha256 is None


def test_missing_explicit_authorization_blocks_before_transport_factory():
    called = False

    def factory(report, env):
        nonlocal called
        called = True
        return DistinctHeartbeatTransport()

    with pytest.raises(ValueError, match="explicit authorization"):
        run_authorized_read_session(
            _request(authorized=False),
            env=_oauth_env(),
            transport_factory=factory,
        )

    assert called is False


def test_invalid_endpoint_blocks_before_transport_creation():
    env = _oauth_env()
    env["LATTICE_ENDPOINT"] = "https://example.invalid"
    called = False

    def factory(report, env):
        nonlocal called
        called = True
        return DistinctHeartbeatTransport()

    with pytest.raises(ValueError, match="preflight"):
        run_authorized_read_session(_request(), env=env, transport_factory=factory)

    assert called is False


def test_receipt_hash_detects_tampering():
    run = run_authorized_read_session(
        _request(attempts=1),
        env=_oauth_env(),
        transport_factory=lambda report, env: DistinctHeartbeatTransport(),
    )
    tampered = run.receipt.model_copy(update={"mission_id": "TAMPERED"})

    assert verify_authorized_read_session_receipt(run.receipt) is True
    assert verify_authorized_read_session_receipt(tampered) is False


def test_export_writes_hash_bound_local_evidence_and_separate_partner_package(tmp_path):
    run = run_authorized_read_session(
        _request(),
        env=_oauth_env(),
        transport_factory=lambda report, env: DistinctHeartbeatTransport(),
    )
    out = tmp_path / "authorized-session"
    manifest = export_authorized_read_session(run, out)

    assert verify_session_artifact_manifest(manifest, out) is True
    assert (out / "manifest.json").is_file()
    assert (out / "session-receipt.json").is_file()
    assert (out / "partner-validation-request.json").is_file()
    assert len(list(out.glob("local-capture-*.json"))) == 3

    all_text = "\n".join(path.read_text() for path in out.glob("*.json"))
    assert "session-client-secret-do-not-leak" not in all_text
    assert "session-sandbox-token-do-not-leak" not in all_text
    assert "session-client-id" not in all_text

    partner = json.loads((out / "partner-validation-request.json").read_text())
    assert "steps" not in partner
    assert partner["live_environment_validated"] is False
    assert manifest.partner_package_excludes_raw_capture_payloads is True

    capture_path = out / "local-capture-01.json"
    capture_path.write_text(capture_path.read_text() + " ")
    assert verify_session_artifact_manifest(manifest, out) is False

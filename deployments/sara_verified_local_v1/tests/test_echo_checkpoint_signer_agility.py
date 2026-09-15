from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from worldshepherd_sara.echo_checkpoint_signer import (
    CHECKPOINT_ALGORITHM_ENV,
    CURRENT_EXECUTABLE_ALGORITHM,
    Ed25519CheckpointSigner,
    EchoCheckpointSignerConfigError,
    EchoCheckpointSignerUnavailable,
    runtime_capabilities,
    signer_from_environment,
)
from worldshepherd_sara.echo_persistence_service import (
    ECHO_TOKEN_FILE_ENV,
    EchoServiceConfigError,
    create_echo_app,
)


def configure_service(monkeypatch, tmp_path):
    data_dir = tmp_path / "echo-agility-data"
    data_dir.mkdir(mode=0o700)
    token = "echo-agility-token-0123456789abcdef0123456789"
    token_path = tmp_path / "echo-agility-token"
    token_path.write_text(token + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv("ECHO_DATA_DIR", str(data_dir.resolve()))
    monkeypatch.setenv(ECHO_TOKEN_FILE_ENV, str(token_path.resolve()))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)
    monkeypatch.delenv("PRIME_SENTINEL_SERVICE_TOKEN", raising=False)
    return token


def test_default_runtime_signer_remains_ed25519(echo_checkpoint_key):
    signer = signer_from_environment()
    assert isinstance(signer, Ed25519CheckpointSigner)
    assert signer.algorithm == "Ed25519"
    assert signer.key_id == "ECHO-CHECKPOINT-PYTEST-V1"
    assert len(signer.fingerprint_sha256) == 64
    public = signer.public_key_record()
    assert public["algorithm"] == "Ed25519"
    assert public["fingerprint_sha256"] == signer.fingerprint_sha256


def test_runtime_capabilities_are_explicitly_not_pq_enabled():
    state = runtime_capabilities()
    assert state["current_executable_algorithm"] == CURRENT_EXECUTABLE_ALGORITHM
    assert set(state["recognized_pq_targets"]) == {"ML-DSA", "SLH-DSA"}
    assert state["pq_runtime_signer_installed"] is False
    assert state["classical_fallback_on_pq_request"] is False
    assert "not implemented" in state["claim_boundary"]


@pytest.mark.parametrize("algorithm", ["ML-DSA", "SLH-DSA"])
def test_recognized_pq_request_fails_closed_without_classical_fallback(
    monkeypatch,
    algorithm,
):
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, algorithm)
    with pytest.raises(EchoCheckpointSignerUnavailable, match="no verified runtime signer adapter"):
        signer_from_environment()


def test_unknown_checkpoint_algorithm_fails_closed(monkeypatch):
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "UNREGISTERED-PQ-SIGNATURE")
    with pytest.raises(EchoCheckpointSignerConfigError, match="unsupported"):
        signer_from_environment()


def test_service_reports_current_checkpoint_agility_state(
    monkeypatch,
    tmp_path,
    echo_checkpoint_key,
):
    token = configure_service(monkeypatch, tmp_path)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "Ed25519")
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(create_echo_app()) as client:
        ready = client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json()["checkpoint_signing_algorithm"] == "Ed25519"
        assert ready.json()["checkpoint_pq_runtime_signer_installed"] is False

        capabilities = client.get("/v1/checkpoint/capabilities", headers=headers)
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert body["current_executable_algorithm"] == "Ed25519"
        assert body["pq_runtime_signer_installed"] is False
        assert body["classical_fallback_on_pq_request"] is False
        assert set(body["recognized_pq_targets"]) == {"ML-DSA", "SLH-DSA"}

        status = client.get("/v1/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["checkpoint_signer"] == body
        assert "PQ checkpoint signing are not claimed" in status.json()["claims_boundary"]


@pytest.mark.parametrize("algorithm", ["ML-DSA", "SLH-DSA"])
def test_service_refuses_to_start_when_unavailable_pq_signer_is_requested(
    monkeypatch,
    tmp_path,
    echo_checkpoint_key,
    algorithm,
):
    configure_service(monkeypatch, tmp_path)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, algorithm)
    with pytest.raises(EchoServiceConfigError, match="no verified runtime signer adapter"):
        create_echo_app()


def test_service_refuses_unknown_signer_algorithm(
    monkeypatch,
    tmp_path,
    echo_checkpoint_key,
):
    configure_service(monkeypatch, tmp_path)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "UNREGISTERED-PQ-SIGNATURE")
    with pytest.raises(EchoServiceConfigError, match="unsupported ECHO checkpoint signing algorithm"):
        create_echo_app()

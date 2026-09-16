from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from worldshepherd_sara.echo_checkpoint_signer import (
    CHECKPOINT_ALGORITHM_ENV,
    CHECKPOINT_SIGNATURE_CONTEXT,
    CURRENT_EXECUTABLE_ALGORITHM,
    Ed25519CheckpointSigner,
    EchoCheckpointSignerConfigError,
    EchoCheckpointSignerUnavailable,
    MLDSA65CheckpointSigner,
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


def test_default_runtime_signer_is_mldsa65(echo_checkpoint_key):
    signer = signer_from_environment()
    assert isinstance(signer, MLDSA65CheckpointSigner)
    assert signer.algorithm == "ML-DSA-65"
    assert signer.key_id == "ECHO-CHECKPOINT-PYTEST-MLDSA65-V1"
    assert len(signer.fingerprint_sha256) == 64
    assert len(signer.public_key_bytes) == 1952
    public = signer.public_key_record()
    assert public["algorithm"] == "ML-DSA-65"
    assert public["signature_context"] == CHECKPOINT_SIGNATURE_CONTEXT.decode("ascii")
    assert public["fingerprint_sha256"] == signer.fingerprint_sha256


def test_runtime_capabilities_report_pq_default_and_no_silent_fallback():
    state = runtime_capabilities()
    assert state["current_executable_algorithm"] == CURRENT_EXECUTABLE_ALGORITHM == "ML-DSA-65"
    assert state["legacy_executable_algorithm"] == "Ed25519"
    assert set(state["recognized_pq_targets"]) == {"ML-DSA", "ML-DSA-65", "SLH-DSA"}
    assert state["pq_runtime_signer_installed"] is True
    assert state["default_runtime_is_post_quantum"] is True
    assert state["classical_fallback_on_pq_request"] is False
    assert state["signature_context"] == "WS-ECHO-CHECKPOINT-V2"


def test_mldsa_alias_selects_verified_mldsa65_signer(monkeypatch, echo_checkpoint_key):
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "ML-DSA")
    signer = signer_from_environment()
    assert isinstance(signer, MLDSA65CheckpointSigner)
    assert signer.algorithm == "ML-DSA-65"


def test_legacy_ed25519_requires_explicit_algorithm_and_matching_key(
    monkeypatch,
    tmp_path,
):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    path = tmp_path / "legacy-ed25519.pem"
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "Ed25519")
    monkeypatch.setenv("ECHO_CHECKPOINT_PRIVATE_KEY_FILE", str(path.resolve()))
    monkeypatch.setenv("ECHO_CHECKPOINT_KEY_ID", "ECHO-LEGACY-ED25519-TEST")
    signer = signer_from_environment()
    assert isinstance(signer, Ed25519CheckpointSigner)
    assert signer.algorithm == "Ed25519"


@pytest.mark.parametrize("algorithm", ["SLH-DSA"])
def test_unavailable_pq_request_fails_closed_without_classical_fallback(
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


def test_mldsa_configuration_rejects_ed25519_key(monkeypatch, tmp_path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    path = tmp_path / "wrong-ed25519.pem"
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "ML-DSA-65")
    monkeypatch.setenv("ECHO_CHECKPOINT_PRIVATE_KEY_FILE", str(path.resolve()))
    monkeypatch.setenv("ECHO_CHECKPOINT_KEY_ID", "ECHO-WRONG-KEY-TEST")
    with pytest.raises(EchoCheckpointSignerConfigError, match="ML-DSA-65 material"):
        signer_from_environment()


def test_service_reports_active_post_quantum_checkpoint_state(
    monkeypatch,
    tmp_path,
    echo_checkpoint_key,
):
    token = configure_service(monkeypatch, tmp_path)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "ML-DSA-65")
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(create_echo_app()) as client:
        ready = client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json()["checkpoint_signing_algorithm"] == "ML-DSA-65"
        assert ready.json()["checkpoint_post_quantum_signature_protection"] is True
        assert ready.json()["checkpoint_pq_runtime_signer_installed"] is True

        capabilities = client.get("/v1/checkpoint/capabilities", headers=headers)
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert body["current_executable_algorithm"] == "ML-DSA-65"
        assert body["pq_runtime_signer_installed"] is True
        assert body["default_runtime_is_post_quantum"] is True
        assert body["classical_fallback_on_pq_request"] is False

        status = client.get("/v1/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["checkpoint_signer"] == body
        assert status.json()["checkpoints"]["post_quantum_signature_protection"] is True
        assert "ML-DSA-65 local checkpoint signing" in status.json()["claims_boundary"]


def test_service_refuses_to_start_when_unavailable_slh_dsa_signer_is_requested(
    monkeypatch,
    tmp_path,
    echo_checkpoint_key,
):
    configure_service(monkeypatch, tmp_path)
    monkeypatch.setenv(CHECKPOINT_ALGORITHM_ENV, "SLH-DSA")
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

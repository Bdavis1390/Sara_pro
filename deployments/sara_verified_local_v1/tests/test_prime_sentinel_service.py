from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.prime_sentinel_authorization import (
    PrimeSentinelAuthorizationAssertion,
    PrimeSentinelVerifier,
)
from worldshepherd_sara.prime_sentinel_issuance_store import (
    REQUEST_ID_HEADER,
    PrimeSentinelIssuanceStoreError,
)
from worldshepherd_sara.prime_sentinel_service import (
    KEY_FILE_ENV,
    KEY_ID_ENV,
    SERVICE_TOKEN_FILE_ENV,
    PrimeSentinelServiceConfigError,
    create_prime_sentinel_app,
)


SERVICE_TOKEN = "prime-sentinel-test-token-that-is-long-and-independent"
KEY_ID = "prime-sentinel-test-key-01"
REQUEST_ID = "PSREQ-test-0001"


def write_ed25519_key(path: Path, mode: int = 0o600) -> Ed25519PrivateKey:
    key = Ed25519PrivateKey.generate()
    data = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(data)
    path.chmod(mode)
    return key


def write_service_token(path: Path, token: str = SERVICE_TOKEN, mode: int = 0o600) -> None:
    path.write_text(token + "\n", encoding="utf-8")
    path.chmod(mode)


def configure(
    monkeypatch,
    key_path: Path,
    token_path: Path,
    *,
    key_id: str = KEY_ID,
    data_dir: Path | None = None,
):
    monkeypatch.setenv(KEY_FILE_ENV, str(key_path))
    monkeypatch.setenv(SERVICE_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.setenv(KEY_ID_ENV, key_id)
    monkeypatch.setenv(
        "PRIME_SENTINEL_DATA_DIR",
        str(data_dir or (key_path.parent / "prime-sentinel-data")),
    )
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)


def configured_files(tmp_path: Path, *, token: str = SERVICE_TOKEN):
    key_path = tmp_path / "sentinel.pem"
    token_path = tmp_path / "service-token"
    write_ed25519_key(key_path)
    write_service_token(token_path, token)
    return key_path, token_path


def auth_headers(request_id: str = REQUEST_ID) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        REQUEST_ID_HEADER: request_id,
    }


def test_service_issues_assertion_accepted_by_existing_sara_verifier(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        public = client.get("/v1/public-key")
        assert public.status_code == 200
        public_body = public.json()
        assert public_body["algorithm"] == "Ed25519"
        assert public_body["key_id"] == KEY_ID

        issued = client.post(
            "/v1/requalification-release",
            headers=auth_headers(),
            json={
                "prime_id": "PRIME-TEST-001",
                "target_environment": "SPACE",
                "lifetime_seconds": 300,
            },
        )
        assert issued.status_code == 200
        assertion = PrimeSentinelAuthorizationAssertion.model_validate(
            issued.json()["assertion"]
        )
        status = client.get(
            f"/v1/issuance/{REQUEST_ID}",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        )
        assert status.status_code == 200
        assert status.json()["state"] == "SIGNED"
        assert status.json()["authorization_id"] == assertion.authorization_id

    verifier = PrimeSentinelVerifier(
        public_keys_b64url={KEY_ID: public_body["public_key_b64url"]}
    )
    verified = verifier.verify(assertion)
    assert verified.prime_id == "PRIME-TEST-001"
    assert verified.target_environment.value == "SPACE"
    assert verified.key_id == KEY_ID
    assert assertion.action == "REQUALIFICATION_RELEASE"


def test_same_request_id_returns_exact_same_signed_assertion_after_restart(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    data_dir = tmp_path / "ledger"
    configure(monkeypatch, key_path, token_path, data_dir=data_dir)
    body = {
        "prime_id": "PRIME-IDEMPOTENT-001",
        "target_environment": "SPACE",
        "lifetime_seconds": 300,
    }

    app1 = create_prime_sentinel_app()
    with TestClient(app1) as client:
        first = client.post(
            "/v1/requalification-release",
            headers=auth_headers("PSREQ-idempotent-001"),
            json=body,
        )
        assert first.status_code == 200
        first_assertion = first.json()["assertion"]

    app2 = create_prime_sentinel_app()
    with TestClient(app2) as client:
        second = client.post(
            "/v1/requalification-release",
            headers=auth_headers("PSREQ-idempotent-001"),
            json=body,
        )
        assert second.status_code == 200
        assert second.json()["assertion"] == first_assertion
        ledger = client.get(
            "/v1/ledger-status",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        )
        assert ledger.status_code == 200
        assert ledger.json()["records"] == 1
        assert ledger.json()["events"] == 2
        assert ledger.json()["event_chain_ok"] is True


def test_request_id_reuse_with_different_parameters_is_conflict(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()
    headers = auth_headers("PSREQ-conflict-001")

    with TestClient(app) as client:
        first = client.post(
            "/v1/requalification-release",
            headers=headers,
            json={"prime_id": "P1", "target_environment": "SPACE"},
        )
        assert first.status_code == 200
        conflict = client.post(
            "/v1/requalification-release",
            headers=headers,
            json={"prime_id": "P2", "target_environment": "SPACE"},
        )
    assert conflict.status_code == 409


def test_missing_or_invalid_request_id_is_rejected(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        missing = client.post(
            "/v1/requalification-release",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
            json={"prime_id": "P1", "target_environment": "SPACE"},
        )
        invalid = client.post(
            "/v1/requalification-release",
            headers=auth_headers("bad"),
            json={"prime_id": "P1", "target_environment": "SPACE"},
        )
    assert missing.status_code == 400
    assert invalid.status_code == 400


def test_signed_persistence_failure_returns_no_assertion_and_retry_recovers_identity(
    tmp_path, monkeypatch
):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()
    store = app.state.issuance_store
    original_mark_signed = store.mark_signed
    observed: dict[str, str] = {}

    def fail_mark_signed(*, request_id, signature_b64url, assertion):
        record = store.get(request_id)
        assert record is not None
        observed["authorization_id"] = record.authorization_id
        raise PrimeSentinelIssuanceStoreError("simulated signed persistence failure")

    monkeypatch.setattr(store, "mark_signed", fail_mark_signed)
    body = {"prime_id": "P-CRASH", "target_environment": "SPACE"}
    headers = auth_headers("PSREQ-crash-window-001")
    with TestClient(app) as client:
        failed = client.post(
            "/v1/requalification-release",
            headers=headers,
            json=body,
        )
        assert failed.status_code == 503
        prepared = store.get("PSREQ-crash-window-001")
        assert prepared is not None
        assert prepared.state == "PREPARED"
        assert prepared.authorization_id == observed["authorization_id"]

        monkeypatch.setattr(store, "mark_signed", original_mark_signed)
        recovered = client.post(
            "/v1/requalification-release",
            headers=headers,
            json=body,
        )
        assert recovered.status_code == 200
        assert recovered.json()["assertion"]["authorization_id"] == observed["authorization_id"]


def test_prepare_persistence_failure_returns_no_assertion(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()
    store = app.state.issuance_store

    def fail_prepare(**_kwargs):
        raise PrimeSentinelIssuanceStoreError("simulated prepare failure")

    monkeypatch.setattr(store, "prepare_or_get", fail_prepare)
    with TestClient(app) as client:
        response = client.post(
            "/v1/requalification-release",
            headers=auth_headers("PSREQ-prepare-fail-001"),
            json={"prime_id": "P1", "target_environment": "SPACE"},
        )
    assert response.status_code == 503
    assert store.get("PSREQ-prepare-fail-001") is None


def test_signing_key_id_cannot_be_rebound_to_different_key_material(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    data_dir = tmp_path / "ledger"
    configure(monkeypatch, key_path, token_path, data_dir=data_dir)
    create_prime_sentinel_app()

    write_ed25519_key(key_path)
    with pytest.raises(
        PrimeSentinelServiceConfigError,
        match="already bound to different key material",
    ):
        create_prime_sentinel_app()


def test_issue_endpoint_requires_independent_bearer(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        missing = client.post(
            "/v1/requalification-release",
            json={"prime_id": "P1", "target_environment": "GROUND"},
        )
        wrong = client.post(
            "/v1/requalification-release",
            headers={"Authorization": "Bearer definitely-wrong-token"},
            json={"prime_id": "P1", "target_environment": "GROUND"},
        )
    assert missing.status_code == 401
    assert wrong.status_code == 403


def test_caller_cannot_inject_action_authorization_id_nonce_or_signature(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        response = client.post(
            "/v1/requalification-release",
            headers=auth_headers(),
            json={
                "prime_id": "P1",
                "target_environment": "SPACE",
                "action": "REQUALIFICATION_RELEASE",
                "authorization_id": "caller-controlled",
                "nonce": "caller-controlled-nonce",
                "signature_b64url": "caller-controlled",
            },
        )
    assert response.status_code == 422


def test_lifetime_above_fifteen_minutes_is_rejected(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        response = client.post(
            "/v1/requalification-release",
            headers=auth_headers(),
            json={
                "prime_id": "P1",
                "target_environment": "SPACE",
                "lifetime_seconds": 901,
            },
        )
    assert response.status_code == 422


def test_insecure_private_key_permissions_are_rejected(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    key_path.chmod(0o644)
    configure(monkeypatch, key_path, token_path)
    with pytest.raises(PrimeSentinelServiceConfigError, match="group/other permissions"):
        create_prime_sentinel_app()


def test_private_key_symlink_is_rejected(tmp_path, monkeypatch):
    real_key, token_path = configured_files(tmp_path)
    symlink = tmp_path / "link.pem"
    symlink.symlink_to(real_key)
    configure(monkeypatch, symlink, token_path)
    with pytest.raises(PrimeSentinelServiceConfigError, match="symbolic link"):
        create_prime_sentinel_app()


def test_relative_private_key_path_is_rejected(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    configure(monkeypatch, Path("sentinel.pem"), token_path)
    with pytest.raises(PrimeSentinelServiceConfigError, match="absolute path"):
        create_prime_sentinel_app()


def test_service_token_file_must_be_secure_long_and_independent(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path, token="too-short")
    configure(monkeypatch, key_path, token_path)
    with pytest.raises(PrimeSentinelServiceConfigError, match="at least 32"):
        create_prime_sentinel_app()

    write_service_token(token_path, SERVICE_TOKEN, mode=0o644)
    with pytest.raises(PrimeSentinelServiceConfigError, match="group/other permissions"):
        create_prime_sentinel_app()

    write_service_token(token_path, SERVICE_TOKEN, mode=0o600)
    monkeypatch.setenv("SARA_ADMIN_TOKEN", SERVICE_TOKEN)
    with pytest.raises(PrimeSentinelServiceConfigError, match="independent"):
        create_prime_sentinel_app()


def test_service_token_symlink_is_rejected(tmp_path, monkeypatch):
    key_path, real_token = configured_files(tmp_path)
    link = tmp_path / "token-link"
    link.symlink_to(real_token)
    configure(monkeypatch, key_path, link)
    with pytest.raises(PrimeSentinelServiceConfigError, match="symbolic link"):
        create_prime_sentinel_app()


def test_health_and_public_surfaces_do_not_disclose_secrets_or_paths(tmp_path, monkeypatch):
    key_path, token_path = configured_files(tmp_path)
    configure(monkeypatch, key_path, token_path)
    app = create_prime_sentinel_app()

    with TestClient(app) as client:
        bodies = [
            client.get("/livez").text,
            client.get("/readyz").text,
            client.get("/v1/public-key").text,
        ]
    combined = "\n".join(bodies)
    assert str(key_path) not in combined
    assert str(token_path) not in combined
    assert "PRIVATE KEY" not in combined
    assert SERVICE_TOKEN not in combined
    assert "issuance_ledger" in bodies[1]


def test_missing_key_configuration_refuses_service_start(tmp_path, monkeypatch):
    token_path = tmp_path / "service-token"
    write_service_token(token_path)
    monkeypatch.delenv(KEY_FILE_ENV, raising=False)
    monkeypatch.setenv(KEY_ID_ENV, KEY_ID)
    monkeypatch.setenv(SERVICE_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.setenv("PRIME_SENTINEL_DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(PrimeSentinelServiceConfigError, match=KEY_FILE_ENV):
        create_prime_sentinel_app()


def test_missing_service_token_file_refuses_service_start(tmp_path, monkeypatch):
    key_path = tmp_path / "sentinel.pem"
    write_ed25519_key(key_path)
    monkeypatch.setenv(KEY_FILE_ENV, str(key_path))
    monkeypatch.setenv(KEY_ID_ENV, KEY_ID)
    monkeypatch.delenv(SERVICE_TOKEN_FILE_ENV, raising=False)
    monkeypatch.setenv("PRIME_SENTINEL_DATA_DIR", str(tmp_path / "data"))
    with pytest.raises(PrimeSentinelServiceConfigError, match=SERVICE_TOKEN_FILE_ENV):
        create_prime_sentinel_app()

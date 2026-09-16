from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_ACTION,
    PrimeSentinelPoOAuthorizationAssertion,
    PrimeSentinelPoOVerifier,
)
from worldshepherd_sara.prime_sentinel_poo_service import create_prime_sentinel_poo_app
from worldshepherd_sara.prime_sentinel_service import (
    KEY_FILE_ENV,
    KEY_ID_ENV,
    SERVICE_TOKEN_FILE_ENV,
)


SERVICE_TOKEN = "prime-sentinel-poo-test-token-that-is-independent-and-long"
KEY_ID = "prime-sentinel-poo-test-key-01"
REQUEST_ID = "PSREQ-poo-service-0001"


def _write_key(path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def _configure(monkeypatch, tmp_path: Path, *, data_dir: Path | None = None):
    key_path = tmp_path / "sentinel.pem"
    token_path = tmp_path / "service-token"
    if not key_path.exists():
        _write_key(key_path)
    token_path.write_text(SERVICE_TOKEN + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv(KEY_FILE_ENV, str(key_path))
    monkeypatch.setenv(SERVICE_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.setenv(KEY_ID_ENV, KEY_ID)
    monkeypatch.setenv("PRIME_SENTINEL_DATA_DIR", str(data_dir or (tmp_path / "ledger")))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)


def _headers(request_id: str = REQUEST_ID):
    return {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-Prime-Sentinel-Request-Id": request_id,
    }


def _scope(asset: str = "asset:alpha"):
    return {
        "asset_id": asset,
        "governance_projection_digest": "sha256:" + "1" * 64,
        "source_decision_digest": "source:decision:001",
        "expected_registry_digest": "2" * 64,
        "candidate_registry_digest": "3" * 64,
        "candidate_state_digest": "state:digest:001",
        "lifetime_seconds": 300,
    }


def test_composite_service_issues_poo_assertion_accepted_by_poo_verifier(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    app = create_prime_sentinel_poo_app()
    with TestClient(app) as client:
        public = client.get("/v1/public-key")
        assert public.status_code == 200
        issued = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers(),
            json=_scope(),
        )
        assert issued.status_code == 200
        assertion = PrimeSentinelPoOAuthorizationAssertion.model_validate(
            issued.json()["assertion"]
        )
        status = client.get(
            f"/v1/poo-issuance/{REQUEST_ID}",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        )
        assert status.status_code == 200
        assert status.json()["state"] == "SIGNED"
        assert status.json()["authorization_id"] == assertion.authorization_id
        ledger = client.get(
            "/v1/poo-ledger-status",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        )
        assert ledger.status_code == 200
        assert ledger.json()["records"] == 1
        assert ledger.json()["signed"] == 1

    verifier = PrimeSentinelPoOVerifier(
        public_keys_b64url={KEY_ID: public.json()["public_key_b64url"]}
    )
    verified = verifier.verify(assertion)
    assert assertion.action == PRIME_SENTINEL_POO_ACTION
    assert verified.asset_id == "asset:alpha"
    assert verified.candidate_registry_digest == "3" * 64


def test_same_poo_request_id_is_exactly_idempotent_across_restart(tmp_path, monkeypatch):
    data_dir = tmp_path / "ledger"
    _configure(monkeypatch, tmp_path, data_dir=data_dir)
    body = _scope()
    app1 = create_prime_sentinel_poo_app()
    with TestClient(app1) as client:
        first = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers("PSREQ-poo-idempotent-001"),
            json=body,
        )
        assert first.status_code == 200
        first_assertion = first.json()["assertion"]

    app2 = create_prime_sentinel_poo_app()
    with TestClient(app2) as client:
        second = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers("PSREQ-poo-idempotent-001"),
            json=body,
        )
        assert second.status_code == 200
        assert second.json()["assertion"] == first_assertion
        ledger = client.get(
            "/v1/poo-ledger-status",
            headers={"Authorization": f"Bearer {SERVICE_TOKEN}"},
        )
        assert ledger.json()["records"] == 1


def test_request_id_reuse_with_different_poo_scope_is_conflict(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    app = create_prime_sentinel_poo_app()
    headers = _headers("PSREQ-poo-conflict-001")
    with TestClient(app) as client:
        first = client.post("/v1/poo-technical-state-commit", headers=headers, json=_scope())
        conflict = client.post(
            "/v1/poo-technical-state-commit",
            headers=headers,
            json=_scope(asset="asset:other"),
        )
    assert first.status_code == 200
    assert conflict.status_code == 409


def test_composite_service_preserves_old_requalification_action(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    app = create_prime_sentinel_poo_app()
    with TestClient(app) as client:
        old = client.post(
            "/v1/requalification-release",
            headers=_headers("PSREQ-old-action-0001"),
            json={"prime_id": "PRIME-OLD-001", "target_environment": "SPACE"},
        )
        new = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers("PSREQ-new-action-0001"),
            json=_scope(),
        )
    assert old.status_code == 200
    assert old.json()["assertion"]["action"] == "REQUALIFICATION_RELEASE"
    assert old.json()["assertion"]["schema"] == "WS-PRIME-SENTINEL-AUTHZ-V1"
    assert new.status_code == 200
    assert new.json()["assertion"]["action"] == PRIME_SENTINEL_POO_ACTION
    assert new.json()["assertion"]["schema"] == "WS-PRIME-SENTINEL-POO-COMMIT-AUTHZ-V1"


def test_poo_issue_endpoint_rejects_caller_injected_authority_fields(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    app = create_prime_sentinel_poo_app()
    injected = _scope()
    injected["authorization_id"] = "caller-controlled"
    injected["action"] = PRIME_SENTINEL_POO_ACTION
    injected["signature_b64url"] = "caller-controlled"
    with TestClient(app) as client:
        response = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers(),
            json=injected,
        )
    assert response.status_code == 422

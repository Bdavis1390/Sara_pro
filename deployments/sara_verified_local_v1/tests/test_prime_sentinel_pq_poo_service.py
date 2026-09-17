from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey
from fastapi.testclient import TestClient

from worldshepherd_sara.prime_sentinel_pq_poo_authorization import (
    PRIME_SENTINEL_PQ_ALGORITHM,
    PRIME_SENTINEL_PQ_STANDARD,
    PrimeSentinelPqPoOAuthorizationAssertion,
    PrimeSentinelPqPoOVerifier,
)
from worldshepherd_sara.prime_sentinel_pq_poo_service import create_prime_sentinel_pq_poo_app
from worldshepherd_sara.prime_sentinel_service import (
    KEY_FILE_ENV,
    KEY_ID_ENV,
    SERVICE_TOKEN_FILE_ENV,
    PrimeSentinelServiceConfigError,
)


SERVICE_TOKEN = "prime-sentinel-pq-test-token-that-is-independent-and-long"
KEY_ID = "prime-sentinel-pq-mldsa65-test-key-01"


def _configure(monkeypatch, tmp_path: Path, *, data_dir: Path | None = None):
    seed_path = tmp_path / "mldsa65-seed.bin"
    token_path = tmp_path / "service-token"
    if not seed_path.exists():
        seed_path.write_bytes(MLDSA65PrivateKey.generate().private_bytes_raw())
        seed_path.chmod(0o600)
    token_path.write_text(SERVICE_TOKEN + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv(KEY_FILE_ENV, str(seed_path))
    monkeypatch.setenv(SERVICE_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.setenv(KEY_ID_ENV, KEY_ID)
    monkeypatch.setenv("PRIME_SENTINEL_DATA_DIR", str(data_dir or (tmp_path / "pq-ledger")))
    monkeypatch.delenv("SARA_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("SARA_RELAY_TOKEN", raising=False)
    return seed_path


def _headers(request_id: str):
    return {
        "Authorization": f"Bearer {SERVICE_TOKEN}",
        "X-Prime-Sentinel-Request-Id": request_id,
    }


def _scope(asset: str = "asset:pq-alpha"):
    return {
        "asset_id": asset,
        "governance_projection_digest": "sha256:" + "1" * 64,
        "source_decision_digest": "source:pq:decision:001",
        "expected_registry_digest": "2" * 64,
        "candidate_registry_digest": "3" * 64,
        "candidate_state_digest": "state:pq:digest:001",
        "lifetime_seconds": 300,
    }


def test_pq_service_issues_real_mldsa65_assertion_accepted_by_verifier(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    app = create_prime_sentinel_pq_poo_app()
    with TestClient(app) as client:
        ready = client.get("/readyz")
        public = client.get("/v1/public-key")
        issued = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers("PSREQ-pq-service-0001"),
            json=_scope(),
        )
    assert ready.status_code == 200
    assert ready.json()["algorithm"] == PRIME_SENTINEL_PQ_ALGORITHM
    assert ready.json()["standard"] == PRIME_SENTINEL_PQ_STANDARD
    assert public.status_code == 200
    assert public.json()["algorithm"] == PRIME_SENTINEL_PQ_ALGORITHM
    assert public.json()["standard"] == PRIME_SENTINEL_PQ_STANDARD
    assert issued.status_code == 200, issued.text
    assertion = PrimeSentinelPqPoOAuthorizationAssertion.model_validate(
        issued.json()["assertion"]
    )
    verifier = PrimeSentinelPqPoOVerifier(
        public_keys_b64url={KEY_ID: public.json()["public_key_b64url"]}
    )
    verified = verifier.verify(assertion)
    assert verified.asset_id == "asset:pq-alpha"
    assert verified.algorithm == PRIME_SENTINEL_PQ_ALGORITHM
    assert verified.standard == PRIME_SENTINEL_PQ_STANDARD


def test_pq_issuance_is_exactly_idempotent_across_service_restart(tmp_path, monkeypatch):
    data_dir = tmp_path / "pq-ledger"
    _configure(monkeypatch, tmp_path, data_dir=data_dir)
    body = _scope()
    headers = _headers("PSREQ-pq-idempotent-0001")
    with TestClient(create_prime_sentinel_pq_poo_app()) as client:
        first = client.post("/v1/poo-technical-state-commit", headers=headers, json=body)
        assert first.status_code == 200
        assertion = first.json()["assertion"]
    with TestClient(create_prime_sentinel_pq_poo_app()) as client:
        second = client.post("/v1/poo-technical-state-commit", headers=headers, json=body)
    assert second.status_code == 200
    assert second.json()["assertion"] == assertion


def test_pq_request_id_reuse_with_different_scope_is_conflict(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    headers = _headers("PSREQ-pq-conflict-0001")
    with TestClient(create_prime_sentinel_pq_poo_app()) as client:
        first = client.post("/v1/poo-technical-state-commit", headers=headers, json=_scope())
        second = client.post(
            "/v1/poo-technical-state-commit",
            headers=headers,
            json=_scope(asset="asset:pq-other"),
        )
    assert first.status_code == 200
    assert second.status_code == 409


def test_pq_service_rejects_caller_injected_signature_fields(tmp_path, monkeypatch):
    _configure(monkeypatch, tmp_path)
    body = _scope()
    body["algorithm"] = "ML-DSA-65"
    body["signature_b64url"] = "caller-controlled"
    with TestClient(create_prime_sentinel_pq_poo_app()) as client:
        response = client.post(
            "/v1/poo-technical-state-commit",
            headers=_headers("PSREQ-pq-injected-0001"),
            json=body,
        )
    assert response.status_code == 422


def test_pq_service_fails_closed_on_wrong_seed_length(tmp_path, monkeypatch):
    seed_path = _configure(monkeypatch, tmp_path)
    seed_path.write_bytes(b"not-a-valid-mldsa65-seed")
    seed_path.chmod(0o600)
    with pytest.raises(PrimeSentinelServiceConfigError, match="exactly 32 raw bytes"):
        create_prime_sentinel_pq_poo_app()

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from worldshepherd_sara.poo_prime_authorized_commit import (
    POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA,
)
from worldshepherd_sara.poo_registry_commit import (
    POO_APPROVAL_INTENT,
    POO_DURABLE_COMMIT_REQUEST_SCHEMA,
    POO_TECHNICAL_REGISTRY_KEY,
)
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
)
from worldshepherd_sara.prime_sentinel_poo_service import create_prime_sentinel_poo_app
from worldshepherd_sara.prime_sentinel_service import (
    KEY_FILE_ENV,
    KEY_ID_ENV,
    SERVICE_TOKEN_FILE_ENV,
)


PRIME_TOKEN = "prime-poo-e2e-service-token-that-is-long-and-independent"
PRIME_KEY_ID = "prime-poo-e2e-key-01"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _bootstrap_body():
    asset_id = "asset:prime-e2e"
    claimant_id = "claimant:prime-e2e"
    key = "key:prime-e2e"
    coc = COCEvidence(
        asset_id=asset_id,
        claimant_id=claimant_id,
        control_key_fingerprint=key,
        custody_reference="custody:prime-e2e",
        custody_point_reference="point:prime-e2e",
        challenge_reference="challenge:prime-e2e",
        observed_at="2026-09-16T07:00:00Z",
        expires_at="2026-09-17T07:00:00Z",
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )
    ownership = OwnershipEvidence(
        asset_id=asset_id,
        claimant_id=claimant_id,
        title_reference="title:prime-e2e",
        control_key_fingerprint=key,
        work_reference="work:prime-e2e",
        concept_reference="concept:prime-e2e",
        coc_reference=evaluate_coc(coc).digest,
        stake_reference="stake:prime-e2e",
        issued_at="2026-09-16T07:00:00Z",
        expires_at="2026-09-17T07:00:00Z",
        asset_fingerprint_bound=True,
        claimant_identity_bound=True,
        title_or_provenance_bound=True,
        pow_verified=True,
        poc_concept_verified=True,
        coc_verified=True,
        pos_bond_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )
    decision = evaluate_governed_bootstrap_commit(
        [], ownership, coc, expected_registry_digest=registry_digest([])
    )
    assert decision.ready is True
    assert decision.commit_decision is not None
    projection = bootstrap_commit_readiness_audit_projection(decision, asset_id=asset_id)
    durable = {
        "schema": POO_DURABLE_COMMIT_REQUEST_SCHEMA,
        "governance_projection": projection,
        "candidate_states": [asdict(state) for state in decision.commit_decision.candidate_states],
        "approval_intent": POO_APPROVAL_INTENT,
        "approval_reference": "approval:prime-e2e:001",
    }
    return durable


def _projection_digest(projection: dict) -> str:
    raw = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _configure_prime(monkeypatch, tmp_path: Path):
    private = Ed25519PrivateKey.generate()
    key_path = tmp_path / "prime-poo-e2e.pem"
    key_path.write_bytes(
        private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    token_path = tmp_path / "prime-poo-e2e-token"
    token_path.write_text(PRIME_TOKEN + "\n", encoding="utf-8")
    token_path.chmod(0o600)
    monkeypatch.setenv(KEY_FILE_ENV, str(key_path))
    monkeypatch.setenv(SERVICE_TOKEN_FILE_ENV, str(token_path))
    monkeypatch.setenv(KEY_ID_ENV, PRIME_KEY_ID)
    monkeypatch.setenv("PRIME_SENTINEL_DATA_DIR", str(tmp_path / "prime-ledger"))


def test_prime_service_to_sara_signed_commit_is_scope_bound_and_audit_custodied(
    client, tokens, monkeypatch, tmp_path
):
    _relay, admin = tokens
    durable = _bootstrap_body()
    projection = durable["governance_projection"]
    _configure_prime(monkeypatch, tmp_path)

    prime_app = create_prime_sentinel_poo_app()
    with TestClient(prime_app) as prime:
        public = prime.get("/v1/public-key")
        assert public.status_code == 200
        issued = prime.post(
            "/v1/poo-technical-state-commit",
            headers={
                "Authorization": f"Bearer {PRIME_TOKEN}",
                "X-Prime-Sentinel-Request-Id": "PSREQ-poo-e2e-0001",
            },
            json={
                "asset_id": projection["asset_id"],
                "governance_projection_digest": _projection_digest(projection),
                "source_decision_digest": projection["source_digest"],
                "expected_registry_digest": projection["expected_registry_digest"],
                "candidate_registry_digest": projection["candidate_registry_digest"],
                "candidate_state_digest": projection["candidate_state_digest"],
                "lifetime_seconds": 300,
            },
        )
        assert issued.status_code == 200
        assertion = issued.json()["assertion"]

    monkeypatch.setenv(
        "PRIME_SENTINEL_PUBLIC_KEYS_JSON",
        json.dumps({PRIME_KEY_ID: public.json()["public_key_b64url"]}),
    )
    monkeypatch.delenv("PRIME_SENTINEL_REVOKED_KEY_IDS", raising=False)

    response = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        headers=_auth(admin),
        json={
            "schema": POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA,
            "durable_commit": durable,
            "prime_authorization": assertion,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["commit"]["status"] == "COMMITTED"
    assert result["commit"]["prime_cryptographic_authorization_verified"] is True
    assert result["commit"]["durable_internal_state_committed"] is True
    assert result["commit"]["legal_title_changed"] is False
    assert result["commit"]["live_value_moved"] is False
    assert result["audit_delivery"] == "DELIVERED"

    raw_registry = client.get("/admin/registry", headers=_auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY in raw_registry
    auths = raw_registry[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]
    assert len(auths) == 1
    consumed = next(iter(auths.values()))
    assert consumed["status"] == "CONSUMED"
    assert consumed["commit_id"] == result["commit"]["commit_id"]
    assert consumed["signed_assertion_sha256"].startswith("sha256:")

    audit = client.get("/v1/audit?limit=50", headers=_auth(admin)).json()["records"]
    technical = [r for r in audit if r.get("event") == "poo_technical_registry_committed"]
    prime_auth = [
        r for r in audit if r.get("event") == "prime_sentinel_poo_authorization_consumed"
    ]
    assert len(technical) == 1
    assert len(prime_auth) == 1
    assert prime_auth[0]["payload"]["signed_assertion_sha256"] == consumed["signed_assertion_sha256"]
    assert prime_auth[0]["payload"]["legal_title_changed"] is False
    assert prime_auth[0]["payload"]["live_value_moved"] is False


def test_consumed_prime_poo_authorization_namespace_is_protected(client, tokens):
    _relay, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers=_auth(admin),
        json={"values": {PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY: {"tamper": True}}},
    )
    assert response.status_code == 403
    registry = client.get("/admin/registry", headers=_auth(admin)).json()["registry"]
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in registry

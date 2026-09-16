from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
    PrimeSentinelPoOAuthorizationAssertion,
    canonical_poo_authorization_message,
)


def bootstrap_body(*, suffix: str = "api"):
    asset_id = f"asset:{suffix}"
    claimant_id = f"claimant:{suffix}"
    key = f"key:{suffix}"
    coc = COCEvidence(
        asset_id=asset_id,
        claimant_id=claimant_id,
        control_key_fingerprint=key,
        custody_reference=f"custody:{suffix}",
        custody_point_reference=f"point:{suffix}",
        challenge_reference=f"challenge:{suffix}",
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
        title_reference=f"title:{suffix}",
        control_key_fingerprint=key,
        work_reference=f"work:{suffix}",
        concept_reference=f"concept:{suffix}",
        coc_reference=evaluate_coc(coc).digest,
        stake_reference=f"stake:{suffix}",
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
        [],
        ownership,
        coc,
        expected_registry_digest=registry_digest([]),
    )
    assert decision.ready is True
    projection = bootstrap_commit_readiness_audit_projection(decision, asset_id=asset_id)
    assert decision.commit_decision is not None
    return {
        "schema": POO_DURABLE_COMMIT_REQUEST_SCHEMA,
        "governance_projection": projection,
        "candidate_states": [asdict(state) for state in decision.commit_decision.candidate_states],
        "approval_intent": POO_APPROVAL_INTENT,
        "approval_reference": f"approval:{suffix}:bootstrap:001",
    }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _projection_digest(projection: dict) -> str:
    raw = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def prime_authorized_body(durable: dict, monkeypatch, *, authorization_id: str = "POO-AUTH-API-001"):
    private = Ed25519PrivateKey.generate()
    key_id = "PS-POO-TEST-01"
    public = _b64url(private.public_key().public_bytes_raw())
    monkeypatch.setenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", json.dumps({key_id: public}))
    monkeypatch.delenv("PRIME_SENTINEL_REVOKED_KEY_IDS", raising=False)

    projection = durable["governance_projection"]
    now = datetime.now(timezone.utc)
    assertion = PrimeSentinelPoOAuthorizationAssertion(
        key_id=key_id,
        authorization_id=authorization_id,
        asset_id=projection["asset_id"],
        governance_projection_digest=_projection_digest(projection),
        source_decision_digest=projection["source_digest"],
        expected_registry_digest=projection["expected_registry_digest"],
        candidate_registry_digest=projection["candidate_registry_digest"],
        candidate_state_digest=projection["candidate_state_digest"],
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="poo-api-nonce-0123456789abcdef",
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_poo_authorization_message(assertion))
    assertion = assertion.model_copy(update={"signature_b64url": _b64url(signature)})
    return {
        "schema": POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA,
        "durable_commit": durable,
        "prime_authorization": assertion.model_dump(mode="json"),
    }


def test_commit_requires_authentication(client):
    response = client.post("/admin/poo/registry/commit", json=bootstrap_body())
    assert response.status_code == 401


def test_relay_role_cannot_commit(client, tokens):
    relay, _admin = tokens
    response = client.post(
        "/admin/poo/registry/commit",
        json=bootstrap_body(),
        headers=auth(relay),
    )
    assert response.status_code == 403


def test_admin_can_commit_genesis_and_audit_delivery_is_custodied(client, tokens):
    _relay, admin = tokens
    response = client.post(
        "/admin/poo/registry/commit",
        json=bootstrap_body(),
        headers=auth(admin),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["commit"]["status"] == "COMMITTED"
    assert body["commit"]["durable_internal_state_committed"] is True
    assert body["commit"]["legal_title_changed"] is False
    assert body["commit"]["live_value_moved"] is False
    assert body["commit"]["credential_rotated"] is False
    assert body["commit"]["external_transfer_executed"] is False
    assert body["audit_delivery"] == "DELIVERED"
    assert body["claims_boundary"] == "INTERNAL_TECHNICAL_REGISTRY_COMMIT_ONLY"

    registry = client.get("/admin/poo/registry", headers=auth(admin))
    assert registry.status_code == 200
    value = registry.json()["registry"]
    assert len(value["states"]) == 1
    assert len(value["commits"]) == 1

    audit = client.get("/v1/audit?limit=50", headers=auth(admin))
    assert audit.status_code == 200
    records = audit.json()["records"]
    commits = [r for r in records if r.get("event") == "poo_technical_registry_committed"]
    assert len(commits) == 1
    payload = commits[0]["payload"]
    assert payload["durable_internal_state_committed"] is True
    assert payload["legal_title_changed"] is False
    assert payload["_delivery_semantics"] == "AT_LEAST_ONCE"


def test_exact_api_retry_is_idempotent(client, tokens):
    _relay, admin = tokens
    request = bootstrap_body()
    first = client.post("/admin/poo/registry/commit", json=request, headers=auth(admin))
    second = client.post("/admin/poo/registry/commit", json=request, headers=auth(admin))
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["commit"]["commit_id"] == second.json()["commit"]["commit_id"]
    assert second.json()["commit"]["status"] == "ALREADY_COMMITTED"
    registry = client.get("/admin/poo/registry", headers=auth(admin)).json()["registry"]
    assert len(registry["states"]) == 1
    assert len(registry["commits"]) == 1


def test_generic_registry_patch_cannot_touch_poo_namespace(client, tokens):
    _relay, admin = tokens
    response = client.patch(
        "/admin/registry",
        json={"values": {POO_TECHNICAL_REGISTRY_KEY: {"tamper": True}}},
        headers=auth(admin),
    )
    assert response.status_code == 403
    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in registry


def test_different_second_genesis_is_permanently_blocked(client, tokens):
    _relay, admin = tokens
    first = bootstrap_body(suffix="first")
    assert client.post("/admin/poo/registry/commit", json=first, headers=auth(admin)).status_code == 200

    second = bootstrap_body(suffix="second")
    response = client.post("/admin/poo/registry/commit", json=second, headers=auth(admin))
    assert response.status_code == 409
    assert "stale PoO registry snapshot" in response.json()["detail"]

    registry = client.get("/admin/poo/registry", headers=auth(admin)).json()["registry"]
    assert len(registry["states"]) == 1
    assert registry["states"][0]["asset_id"] == "asset:first"


def test_unknown_projection_claim_is_rejected_before_transaction(client, tokens):
    _relay, admin = tokens
    body = bootstrap_body()
    body["governance_projection"]["government_title_authorized"] = True
    response = client.post("/admin/poo/registry/commit", json=body, headers=auth(admin))
    assert response.status_code == 422
    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in registry


def test_wrong_approval_intent_is_rejected_before_transaction(client, tokens):
    _relay, admin = tokens
    body = bootstrap_body()
    body["approval_intent"] = "MOVE_LIVE_VALUE"
    response = client.post("/admin/poo/registry/commit", json=body, headers=auth(admin))
    assert response.status_code == 422
    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in registry


def test_prime_authorized_commit_requires_admin_and_configured_trust(client, tokens, monkeypatch):
    relay, admin = tokens
    durable = bootstrap_body(suffix="signed-auth")
    signed = prime_authorized_body(durable, monkeypatch)

    relay_response = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(relay),
    )
    assert relay_response.status_code == 403

    monkeypatch.setenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", "{}")
    unavailable = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(admin),
    )
    assert unavailable.status_code == 503


def test_prime_authorized_commit_persists_state_consumed_auth_and_two_audit_events(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    signed = prime_authorized_body(bootstrap_body(suffix="signed"), monkeypatch)
    response = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(admin),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["commit"]["status"] == "COMMITTED"
    assert body["commit"]["prime_cryptographic_authorization_verified"] is True
    assert body["commit"]["legal_title_changed"] is False
    assert body["commit"]["live_value_moved"] is False
    assert body["audit_delivery"] == "DELIVERED"

    raw_registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    auths = raw_registry[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]
    assert len(auths) == 1
    consumed = next(iter(auths.values()))
    assert consumed["status"] == "CONSUMED"
    assert consumed["commit_id"] == body["commit"]["commit_id"]

    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    commits = [r for r in audit if r.get("event") == "poo_technical_registry_committed"]
    authorizations = [
        r for r in audit if r.get("event") == "prime_sentinel_poo_authorization_consumed"
    ]
    assert len(commits) == 1
    assert len(authorizations) == 1
    assert authorizations[0]["payload"]["prime_cryptographic_authorization_verified"] is True
    assert authorizations[0]["payload"]["legal_title_changed"] is False
    assert authorizations[0]["payload"]["_delivery_semantics"] == "AT_LEAST_ONCE"


def test_prime_authorized_exact_retry_does_not_duplicate_state_or_audit(client, tokens, monkeypatch):
    _relay, admin = tokens
    signed = prime_authorized_body(bootstrap_body(suffix="signed-retry"), monkeypatch)
    first = client.post(
        "/admin/poo/registry/commit-prime-authorized", json=signed, headers=auth(admin)
    )
    second = client.post(
        "/admin/poo/registry/commit-prime-authorized", json=signed, headers=auth(admin)
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["commit"]["status"] == "ALREADY_COMMITTED"
    assert first.json()["commit"]["commit_id"] == second.json()["commit"]["commit_id"]

    registry = client.get("/admin/poo/registry", headers=auth(admin)).json()["registry"]
    assert len(registry["states"]) == 1
    assert len(registry["commits"]) == 1
    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert len([r for r in audit if r.get("event") == "poo_technical_registry_committed"]) == 1
    assert len(
        [r for r in audit if r.get("event") == "prime_sentinel_poo_authorization_consumed"]
    ) == 1


def test_prime_authorized_tampered_scope_is_rejected_without_state_mutation(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    signed = prime_authorized_body(bootstrap_body(suffix="signed-tamper"), monkeypatch)
    signed["prime_authorization"]["candidate_state_digest"] = "tampered-state-digest"
    response = client.post(
        "/admin/poo/registry/commit-prime-authorized", json=signed, headers=auth(admin)
    )
    assert response.status_code == 409
    registry = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in registry
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in registry


def test_requalification_release_assertion_shape_cannot_authorize_poo_commit(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="old-action")
    signed = prime_authorized_body(durable, monkeypatch)
    signed["prime_authorization"] = {
        "schema": "WS-PRIME-SENTINEL-AUTHZ-V1",
        "issuer": "PRIME_SENTINEL",
        "key_id": "PS-POO-TEST-01",
        "authorization_id": "OLD-AUTH-001",
        "prime_id": "PRIME-001",
        "action": "REQUALIFICATION_RELEASE",
        "target_environment": "SPACE",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        "nonce": "old-action-nonce-0123456789",
        "signature_b64url": _b64url(b"0" * 64),
    }
    response = client.post(
        "/admin/poo/registry/commit-prime-authorized", json=signed, headers=auth(admin)
    )
    assert response.status_code == 422

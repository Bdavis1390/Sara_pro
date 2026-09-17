from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from worldshepherd_sara.poo_prime_authorized_commit import POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA
from worldshepherd_sara.poo_registry_commit import (
    POO_APPROVAL_INTENT,
    POO_DURABLE_COMMIT_REQUEST_SCHEMA,
    POO_TECHNICAL_REGISTRY_KEY,
)
from worldshepherd_sara.poo_registry_commit_api import poo_prime_authorization_required
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
    PrimeSentinelPoOAuthorizationAssertion,
    canonical_poo_authorization_message,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _durable_body() -> dict:
    asset = "asset:prime-required-policy"
    claimant = "claimant:prime-required-policy"
    key = "key:prime-required-policy"
    coc = COCEvidence(
        asset_id=asset,
        claimant_id=claimant,
        control_key_fingerprint=key,
        custody_reference="custody:prime-required-policy",
        custody_point_reference="point:prime-required-policy",
        challenge_reference="challenge:prime-required-policy",
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
        asset_id=asset,
        claimant_id=claimant,
        title_reference="title:prime-required-policy",
        control_key_fingerprint=key,
        work_reference="work:prime-required-policy",
        concept_reference="concept:prime-required-policy",
        coc_reference=evaluate_coc(coc).digest,
        stake_reference="stake:prime-required-policy",
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
    assert decision.ready is True and decision.commit_decision is not None
    projection = bootstrap_commit_readiness_audit_projection(decision, asset_id=asset)
    return {
        "schema": POO_DURABLE_COMMIT_REQUEST_SCHEMA,
        "governance_projection": projection,
        "candidate_states": [asdict(state) for state in decision.commit_decision.candidate_states],
        "approval_intent": POO_APPROVAL_INTENT,
        "approval_reference": "approval:prime-required-policy:001",
    }


def _signed_body(durable: dict, monkeypatch: pytest.MonkeyPatch) -> dict:
    private = Ed25519PrivateKey.generate()
    key_id = "PS-POO-REQUIRED-TEST"
    monkeypatch.setenv(
        "PRIME_SENTINEL_PUBLIC_KEYS_JSON",
        json.dumps({key_id: _b64url(private.public_key().public_bytes_raw())}),
    )
    monkeypatch.delenv("PRIME_SENTINEL_REVOKED_KEY_IDS", raising=False)
    projection = durable["governance_projection"]
    raw = json.dumps(
        projection, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    now = datetime.now(timezone.utc)
    assertion = PrimeSentinelPoOAuthorizationAssertion(
        key_id=key_id,
        authorization_id="POO-AUTH-REQUIRED-001",
        asset_id=projection["asset_id"],
        governance_projection_digest="sha256:" + hashlib.sha256(raw).hexdigest(),
        source_decision_digest=projection["source_digest"],
        expected_registry_digest=projection["expected_registry_digest"],
        candidate_registry_digest=projection["candidate_registry_digest"],
        candidate_state_digest=projection["candidate_state_digest"],
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce="prime-required-nonce-0123456789abcdef",
        signature_b64url=_b64url(b"0" * 64),
    )
    assertion = assertion.model_copy(
        update={
            "signature_b64url": _b64url(
                private.sign(canonical_poo_authorization_message(assertion))
            )
        }
    )
    return {
        "schema": POO_PRIME_AUTHORIZED_COMMIT_REQUEST_SCHEMA,
        "durable_commit": durable,
        "prime_authorization": assertion.model_dump(mode="json"),
    }


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_prime_required_policy_truthy_values(monkeypatch, value):
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", value)
    assert poo_prime_authorization_required() is True


@pytest.mark.parametrize("value", ["", "0", "false", "FALSE", "no", "off"])
def test_prime_required_policy_false_values(monkeypatch, value):
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", value)
    assert poo_prime_authorization_required() is False


def test_invalid_prime_required_policy_fails_closed(monkeypatch):
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "sometimes")
    with pytest.raises(RuntimeError, match="POO_REQUIRE_PRIME_AUTHORIZATION"):
        poo_prime_authorization_required()


def test_enforced_policy_blocks_unsigned_before_mutation_then_allows_signed(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "1")
    durable = _durable_body()

    before = client.get("/admin/registry", headers=_auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in before
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in before

    unsigned = client.post(
        "/admin/poo/registry/commit", json=durable, headers=_auth(admin)
    )
    assert unsigned.status_code == 403
    assert "disabled by policy" in unsigned.json()["detail"]

    after_unsigned = client.get("/admin/registry", headers=_auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in after_unsigned
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in after_unsigned
    audit_before_signed = client.get("/v1/audit?limit=50", headers=_auth(admin)).json()["records"]
    assert not [r for r in audit_before_signed if r.get("event") == "poo_technical_registry_committed"]
    assert not [
        r
        for r in audit_before_signed
        if r.get("event") == "prime_sentinel_poo_authorization_consumed"
    ]

    signed = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=_signed_body(durable, monkeypatch),
        headers=_auth(admin),
    )
    assert signed.status_code == 200
    body = signed.json()
    assert body["prime_authorization_required"] is True
    assert body["commit"]["status"] == "COMMITTED"
    assert body["commit"]["prime_cryptographic_authorization_verified"] is True

    registry_view = client.get("/admin/poo/registry", headers=_auth(admin)).json()
    assert registry_view["prime_authorization_required"] is True
    assert len(registry_view["registry"]["states"]) == 1
    assert len(registry_view["registry"]["commits"]) == 1


def test_invalid_policy_blocks_both_mutation_routes(client, tokens, monkeypatch):
    _relay, admin = tokens
    durable = _durable_body()
    signed = _signed_body(durable, monkeypatch)
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "invalid")

    unsigned = client.post(
        "/admin/poo/registry/commit", json=durable, headers=_auth(admin)
    )
    prime = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=_auth(admin),
    )
    assert unsigned.status_code == 503
    assert prime.status_code == 503

    registry = client.get("/admin/registry", headers=_auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in registry
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in registry

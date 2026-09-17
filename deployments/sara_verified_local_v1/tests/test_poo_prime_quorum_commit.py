from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from deployments.sara_verified_local_v1.tests.test_poo_registry_commit_api import (
    auth,
    bootstrap_body,
)
from worldshepherd_sara.event_outbox import EVENT_OUTBOX_REGISTRY_KEY, queue_event_outbox_patch
from worldshepherd_sara.poo_prime_quorum_commit import (
    POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA,
)
from worldshepherd_sara.poo_registry_commit import POO_TECHNICAL_REGISTRY_KEY
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
    PrimeSentinelPoOAuthorizationAssertion,
    canonical_poo_authorization_message,
)


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


def _signed_assertion(
    durable: dict,
    private: Ed25519PrivateKey,
    *,
    key_id: str,
    authorization_id: str,
    nonce: str,
    scope_override: dict | None = None,
):
    projection = durable["governance_projection"]
    scope = {
        "asset_id": projection["asset_id"],
        "governance_projection_digest": _projection_digest(projection),
        "source_decision_digest": projection["source_digest"],
        "expected_registry_digest": projection["expected_registry_digest"],
        "candidate_registry_digest": projection["candidate_registry_digest"],
        "candidate_state_digest": projection["candidate_state_digest"],
    }
    scope.update(scope_override or {})
    now = datetime.now(timezone.utc)
    assertion = PrimeSentinelPoOAuthorizationAssertion(
        key_id=key_id,
        authorization_id=authorization_id,
        **scope,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url=_b64url(b"0" * 64),
    )
    signature = private.sign(canonical_poo_authorization_message(assertion))
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def _quorum_body(durable: dict, *, scope_override_second: dict | None = None):
    key1 = Ed25519PrivateKey.generate()
    key2 = Ed25519PrivateKey.generate()
    assertions = [
        _signed_assertion(
            durable,
            key1,
            key_id="PS-QUORUM-K1",
            authorization_id="POO-QUORUM-AUTH-1",
            nonce="quorum-nonce-000000000000001",
        ),
        _signed_assertion(
            durable,
            key2,
            key_id="PS-QUORUM-K2",
            authorization_id="POO-QUORUM-AUTH-2",
            nonce="quorum-nonce-000000000000002",
            scope_override=scope_override_second,
        ),
    ]
    public = {
        "PS-QUORUM-K1": _b64url(key1.public_key().public_bytes_raw()),
        "PS-QUORUM-K2": _b64url(key2.public_key().public_bytes_raw()),
    }
    return (
        {
            "schema": POO_PRIME_QUORUM_COMMIT_REQUEST_SCHEMA,
            "durable_commit": durable,
            "prime_authorizations": [item.model_dump(mode="json") for item in assertions],
        },
        public,
    )


def _configure(monkeypatch, public: dict[str, str], *, threshold: str = "2", revoked: str = ""):
    monkeypatch.setenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", json.dumps(public))
    monkeypatch.setenv("POO_PRIME_QUORUM_THRESHOLD", threshold)
    if revoked:
        monkeypatch.setenv("PRIME_SENTINEL_REVOKED_KEY_IDS", revoked)
    else:
        monkeypatch.delenv("PRIME_SENTINEL_REVOKED_KEY_IDS", raising=False)


def test_two_distinct_signers_commit_exact_threshold_and_audit_quorum(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-ok"))
    _configure(monkeypatch, public)

    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["prime_quorum_threshold"] == 2
    assert result["commit"]["status"] == "COMMITTED"
    assert result["commit"]["quorum_threshold"] == 2
    assert result["commit"]["quorum_size"] == 2
    assert result["commit"]["prime_quorum_cryptographic_authorization_verified"] is True
    assert result["commit"]["single_signer_sufficient"] is False
    assert result["commit"]["legal_title_changed"] is False
    assert result["commit"]["live_value_moved"] is False
    assert len(set(result["commit"]["prime_signing_key_ids"])) == 2

    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert len(raw[POO_TECHNICAL_REGISTRY_KEY]["states"]) == 1
    assert len(raw[POO_TECHNICAL_REGISTRY_KEY]["commits"]) == 1
    assert len(raw[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]) == 2

    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert len([r for r in audit if r.get("event") == "poo_technical_registry_committed"]) == 1
    quorum = [
        r for r in audit
        if r.get("event") == "prime_sentinel_poo_quorum_authorizations_consumed"
    ]
    assert len(quorum) == 1
    assert quorum[0]["payload"]["quorum_threshold"] == 2
    assert quorum[0]["payload"]["quorum_size"] == 2
    assert quorum[0]["payload"]["single_signer_sufficient"] is False


def test_exact_quorum_retry_is_idempotent_and_does_not_duplicate_audit(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-retry"))
    _configure(monkeypatch, public)
    first = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    second = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["commit"]["status"] == "COMMITTED"
    assert second.json()["commit"]["status"] == "ALREADY_COMMITTED"
    assert first.json()["commit"]["commit_id"] == second.json()["commit"]["commit_id"]
    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert len([r for r in audit if r.get("event") == "poo_technical_registry_committed"]) == 1
    assert len(
        [r for r in audit if r.get("event") == "prime_sentinel_poo_quorum_authorizations_consumed"]
    ) == 1


def test_one_signer_cannot_satisfy_configured_two_signer_quorum(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-one"))
    body["prime_authorizations"] = body["prime_authorizations"][:1]
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 422
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw


def test_request_cannot_supply_or_lower_quorum_threshold(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-no-downgrade"))
    body["quorum_threshold"] = 1
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 422


def test_duplicate_signing_key_id_is_rejected_before_transaction(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-duplicate-key"))
    body["prime_authorizations"][1]["key_id"] = body["prime_authorizations"][0]["key_id"]
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 422


def test_duplicate_authorization_id_or_nonce_is_rejected_before_transaction(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    for field in ("authorization_id", "nonce"):
        body, public = _quorum_body(bootstrap_body(suffix=f"quorum-dup-{field}"))
        body["prime_authorizations"][1][field] = body["prime_authorizations"][0][field]
        _configure(monkeypatch, public)
        response = client.post(
            "/admin/poo/registry/commit-prime-quorum-authorized",
            headers=auth(admin),
            json=body,
        )
        assert response.status_code == 422


def test_one_bad_signature_aborts_entire_quorum_transaction(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-bad-signature"))
    body["prime_authorizations"][1]["signature_b64url"] = _b64url(b"x" * 64)
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw


def test_one_scope_mismatch_aborts_entire_quorum_transaction(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(
        bootstrap_body(suffix="quorum-scope"),
        scope_override_second={"candidate_state_digest": "state:wrong-quorum-scope"},
    )
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    assert "scope mismatch" in response.json()["detail"]
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw


def test_revoked_quorum_member_aborts_entire_transaction(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-revoked"))
    _configure(monkeypatch, public, revoked="PS-QUORUM-K2")
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    assert "revoked" in response.json()["detail"]
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw


def test_forged_quorum_member_cannot_claim_already_committed_retry(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-fingerprint"))
    _configure(monkeypatch, public)
    first = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert first.status_code == 200
    forged = json.loads(json.dumps(body))
    forged["prime_authorizations"][1]["signature_b64url"] = _b64url(b"x" * 64)
    replay = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=forged,
    )
    assert replay.status_code == 409
    assert "signed_assertion_sha256" in replay.json()["detail"]
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert len(raw[POO_TECHNICAL_REGISTRY_KEY]["states"]) == 1
    assert len(raw[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]) == 2


def test_one_remaining_outbox_slot_aborts_state_and_all_quorum_consumption(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    store = client.app.state.store

    def seed(registry):
        working = dict(registry)
        patch = {}
        for index in range(31):
            event_patch, _ = queue_event_outbox_patch(
                working,
                event="quorum_capacity_seed",
                actor="test",
                event_id=f"SARA-EVENT-QUORUM-CAPACITY-{index:02d}",
                payload={"index": index},
            )
            working.update(event_patch)
            patch.update(event_patch)
        return patch, True

    assert store.transact_registry(seed) is True
    before = store.get_registry()
    assert len(before[EVENT_OUTBOX_REGISTRY_KEY]) == 31

    body, public = _quorum_body(bootstrap_body(suffix="quorum-capacity"))
    _configure(monkeypatch, public)
    response = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 503
    after = store.get_registry()
    assert POO_TECHNICAL_REGISTRY_KEY not in after
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in after
    assert after[EVENT_OUTBOX_REGISTRY_KEY] == before[EVENT_OUTBOX_REGISTRY_KEY]


def test_missing_or_invalid_quorum_threshold_fails_closed(client, tokens, monkeypatch):
    _relay, admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-threshold-config"))
    monkeypatch.setenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", json.dumps(public))
    monkeypatch.delenv("POO_PRIME_QUORUM_THRESHOLD", raising=False)
    missing = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert missing.status_code == 503
    monkeypatch.setenv("POO_PRIME_QUORUM_THRESHOLD", "1")
    invalid = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=body,
    )
    assert invalid.status_code == 503


def test_quorum_route_requires_admin(client, tokens, monkeypatch):
    relay, _admin = tokens
    body, public = _quorum_body(bootstrap_body(suffix="quorum-auth"))
    _configure(monkeypatch, public)
    assert client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        json=body,
    ).status_code == 401
    assert client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        json=body,
        headers=auth(relay),
    ).status_code == 403

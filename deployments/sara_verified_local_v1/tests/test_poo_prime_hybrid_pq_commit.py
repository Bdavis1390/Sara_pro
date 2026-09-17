from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from deployments.sara_verified_local_v1.tests.test_poo_prime_quorum_commit import (
    _b64url,
    _projection_digest,
    _quorum_body,
)
from deployments.sara_verified_local_v1.tests.test_poo_registry_commit_api import (
    auth,
    bootstrap_body,
)
from worldshepherd_sara.poo_prime_hybrid_pq_commit import (
    POO_PRIME_HYBRID_PQ_COMMIT_REQUEST_SCHEMA,
)
from worldshepherd_sara.poo_registry_commit import POO_TECHNICAL_REGISTRY_KEY
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
)
from worldshepherd_sara.prime_sentinel_pq_poo_authorization import (
    PRIME_SENTINEL_PQ_CONTEXT,
    PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY,
    PrimeSentinelPqPoOAuthorizationAssertion,
    canonical_pq_poo_authorization_message,
)


def _pq_assertion(
    durable: dict,
    private: MLDSA65PrivateKey,
    *,
    key_id: str = "PS-PQ-MLDSA65-K1",
    authorization_id: str = "POO-PQ-AUTH-1",
    nonce: str = "pq-hybrid-nonce-000000000000001",
    scope_override: dict | None = None,
) -> PrimeSentinelPqPoOAuthorizationAssertion:
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
    assertion = PrimeSentinelPqPoOAuthorizationAssertion(
        key_id=key_id,
        authorization_id=authorization_id,
        **scope,
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
        nonce=nonce,
        signature_b64url=_b64url(b"0" * 3309),
    )
    signature = private.sign(
        canonical_pq_poo_authorization_message(assertion),
        context=PRIME_SENTINEL_PQ_CONTEXT,
    )
    return assertion.model_copy(update={"signature_b64url": _b64url(signature)})


def _hybrid_body(durable: dict, *, pq_scope_override: dict | None = None):
    quorum, classical_public = _quorum_body(durable)
    pq_private = MLDSA65PrivateKey.generate()
    pq = _pq_assertion(durable, pq_private, scope_override=pq_scope_override)
    return (
        {
            "schema": POO_PRIME_HYBRID_PQ_COMMIT_REQUEST_SCHEMA,
            "durable_commit": durable,
            "prime_authorizations": quorum["prime_authorizations"],
            "pq_authorization": pq.model_dump(mode="json"),
        },
        quorum,
        classical_public,
        {pq.key_id: _b64url(pq_private.public_key().public_bytes_raw())},
    )


def _configure_hybrid(monkeypatch, classical_public: dict, pq_public: dict, *, revoked_pq: str = ""):
    monkeypatch.setenv("PRIME_SENTINEL_PUBLIC_KEYS_JSON", json.dumps(classical_public))
    monkeypatch.setenv("PRIME_SENTINEL_PQ_PUBLIC_KEYS_JSON", json.dumps(pq_public))
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "1")
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "1")
    monkeypatch.setenv("POO_PRIME_QUORUM_THRESHOLD", "2")
    monkeypatch.setenv("POO_REQUIRE_PRIME_HYBRID_PQ", "1")
    monkeypatch.setenv("PRIME_SENTINEL_PQ_REVOKED_KEY_IDS", revoked_pq)


def test_hybrid_requires_two_classical_signers_plus_real_mldsa65_and_replays_exactly(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="hybrid-pq-ok")
    body, _quorum, classical_public, pq_public = _hybrid_body(durable)
    _configure_hybrid(monkeypatch, classical_public, pq_public)

    first = client.post(
        "/admin/poo/registry/commit-prime-hybrid-pq-authorized",
        headers=auth(admin),
        json=body,
    )
    assert first.status_code == 200, first.text
    commit = first.json()["commit"]
    assert commit["status"] == "COMMITTED"
    assert commit["classical_quorum_threshold"] == 2
    assert commit["classical_quorum_size"] == 2
    assert commit["pq_algorithm"] == "ML-DSA-65"
    assert commit["pq_standard"] == "FIPS-204"
    assert commit["classical_quorum_cryptographic_authorization_verified"] is True
    assert commit["pq_cryptographic_authorization_verified"] is True
    assert commit["hybrid_cryptographic_authorization_verified"] is True
    assert commit["single_classical_signer_sufficient"] is False
    assert commit["pq_only_sufficient"] is False
    assert commit["algorithm_downgrade_permitted"] is False

    second = client.post(
        "/admin/poo/registry/commit-prime-hybrid-pq-authorized",
        headers=auth(admin),
        json=body,
    )
    assert second.status_code == 200, second.text
    assert second.json()["commit"]["status"] == "ALREADY_COMMITTED"
    assert second.json()["commit"]["commit_id"] == commit["commit_id"]

    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert len(raw[POO_TECHNICAL_REGISTRY_KEY]["states"]) == 1
    assert len(raw[POO_TECHNICAL_REGISTRY_KEY]["commits"]) == 1
    assert len(raw[PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY]) == 2
    assert len(raw[PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY]) == 1

    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert len([r for r in audit if r.get("event") == "poo_technical_registry_committed"]) == 1
    assert len([r for r in audit if r.get("event") == "prime_sentinel_poo_quorum_authorizations_consumed"]) == 1
    hybrid = [
        r for r in audit
        if r.get("event") == "prime_sentinel_poo_hybrid_pq_authorization_consumed"
    ]
    assert len(hybrid) == 1
    assert hybrid[0]["payload"]["pq_algorithm"] == "ML-DSA-65"
    assert hybrid[0]["payload"]["pq_standard"] == "FIPS-204"
    assert hybrid[0]["payload"]["algorithm_downgrade_permitted"] is False


def test_hybrid_policy_blocks_unsigned_and_classical_only_quorum_before_mutation(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="hybrid-pq-downgrade")
    _body, quorum, classical_public, pq_public = _hybrid_body(durable)
    _configure_hybrid(monkeypatch, classical_public, pq_public)

    unsigned = client.post(
        "/admin/poo/registry/commit",
        headers=auth(admin),
        json=durable,
    )
    classical_only = client.post(
        "/admin/poo/registry/commit-prime-quorum-authorized",
        headers=auth(admin),
        json=quorum,
    )
    assert unsigned.status_code == 403
    assert classical_only.status_code == 403
    assert "hybrid PQ" in classical_only.text
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY not in raw


def test_tampered_pq_signature_aborts_entire_hybrid_transaction(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="hybrid-pq-tamper")
    body, _quorum, classical_public, pq_public = _hybrid_body(durable)
    _configure_hybrid(monkeypatch, classical_public, pq_public)
    signature = body["pq_authorization"]["signature_b64url"]
    body["pq_authorization"]["signature_b64url"] = (
        ("A" if signature[:1] != "A" else "B") + signature[1:]
    )

    response = client.post(
        "/admin/poo/registry/commit-prime-hybrid-pq-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY not in raw


def test_valid_pq_signature_with_wrong_commit_scope_aborts_atomically(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="hybrid-pq-scope")
    body, _quorum, classical_public, pq_public = _hybrid_body(
        durable,
        pq_scope_override={"candidate_state_digest": "sha256:wrong-pq-scope"},
    )
    _configure_hybrid(monkeypatch, classical_public, pq_public)
    response = client.post(
        "/admin/poo/registry/commit-prime-hybrid-pq-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY not in raw


def test_revoked_pq_key_aborts_entire_hybrid_transaction(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="hybrid-pq-revoked")
    body, _quorum, classical_public, pq_public = _hybrid_body(durable)
    pq_key_id = body["pq_authorization"]["key_id"]
    _configure_hybrid(monkeypatch, classical_public, pq_public, revoked_pq=pq_key_id)
    response = client.post(
        "/admin/poo/registry/commit-prime-hybrid-pq-authorized",
        headers=auth(admin),
        json=body,
    )
    assert response.status_code == 409
    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_PQ_POO_AUTHZ_REGISTRY_KEY not in raw


def test_hybrid_policy_fails_closed_if_quorum_policy_is_disabled(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    monkeypatch.setenv("POO_REQUIRE_PRIME_HYBRID_PQ", "1")
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "0")
    response = client.get("/admin/poo/registry", headers=auth(admin))
    assert response.status_code == 503
    assert "requires POO_REQUIRE_PRIME_QUORUM=1" in response.text

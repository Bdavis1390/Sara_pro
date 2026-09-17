from __future__ import annotations

from deployments.sara_verified_local_v1.tests.test_poo_registry_commit_api import (
    auth,
    bootstrap_body,
    prime_authorized_body,
)
from worldshepherd_sara.poo_registry_commit import POO_TECHNICAL_REGISTRY_KEY
from worldshepherd_sara.poo_registry_commit_api import (
    poo_prime_quorum_required,
    poo_prime_quorum_threshold,
)
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
)


def _enable_quorum(monkeypatch, *, threshold: str = "2"):
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "1")
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "1")
    monkeypatch.setenv("POO_PRIME_QUORUM_THRESHOLD", threshold)


def test_quorum_policy_parser_and_threshold(monkeypatch):
    _enable_quorum(monkeypatch)
    assert poo_prime_quorum_required() is True
    assert poo_prime_quorum_threshold() == 2


def test_quorum_policy_blocks_unsigned_and_single_signer_before_mutation(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    durable = bootstrap_body(suffix="quorum-policy-block")
    signed = prime_authorized_body(durable, monkeypatch)
    _enable_quorum(monkeypatch)

    unsigned = client.post(
        "/admin/poo/registry/commit",
        json=durable,
        headers=auth(admin),
    )
    assert unsigned.status_code == 403
    assert "quorum policy" in unsigned.json()["detail"]

    single = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(admin),
    )
    assert single.status_code == 403
    assert "Single-signer" in single.json()["detail"]

    raw = client.get("/admin/registry", headers=auth(admin)).json()["registry"]
    assert POO_TECHNICAL_REGISTRY_KEY not in raw
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in raw
    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert not [r for r in audit if r.get("event") == "poo_technical_registry_committed"]
    assert not [
        r for r in audit
        if r.get("event") in {
            "prime_sentinel_poo_authorization_consumed",
            "prime_sentinel_poo_quorum_authorizations_consumed",
        }
    ]


def test_registry_view_exposes_effective_quorum_policy(client, tokens, monkeypatch):
    _relay, admin = tokens
    monkeypatch.setenv("POO_REQUIRE_PRIME_AUTHORIZATION", "0")
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "1")
    monkeypatch.setenv("POO_PRIME_QUORUM_THRESHOLD", "2")
    response = client.get("/admin/poo/registry", headers=auth(admin))
    assert response.status_code == 200
    body = response.json()
    assert body["prime_authorization_required"] is True
    assert body["prime_quorum_required"] is True
    assert body["prime_quorum_threshold"] == 2


def test_quorum_required_without_threshold_fails_closed_for_registry_and_mutation(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "1")
    monkeypatch.delenv("POO_PRIME_QUORUM_THRESHOLD", raising=False)
    assert client.get("/admin/poo/registry", headers=auth(admin)).status_code == 503
    response = client.post(
        "/admin/poo/registry/commit",
        json=bootstrap_body(suffix="quorum-missing-threshold"),
        headers=auth(admin),
    )
    assert response.status_code == 503


def test_invalid_quorum_policy_value_fails_closed(client, tokens, monkeypatch):
    _relay, admin = tokens
    monkeypatch.setenv("POO_REQUIRE_PRIME_QUORUM", "sometimes")
    response = client.get("/admin/poo/registry", headers=auth(admin))
    assert response.status_code == 503
    assert "POO_REQUIRE_PRIME_QUORUM" in response.json()["detail"]

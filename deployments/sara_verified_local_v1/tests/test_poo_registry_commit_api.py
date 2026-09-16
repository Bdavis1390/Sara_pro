from __future__ import annotations

from dataclasses import asdict

from security.poo.bootstrap_audit_projection import bootstrap_commit_readiness_audit_projection
from security.poo.bootstrap_governance_guard import evaluate_governed_bootstrap_commit
from security.poo.coc_guard import COCEvidence, evaluate_coc
from security.poo.ownership_guard import OwnershipEvidence
from security.poo.registry_guard import registry_digest
from worldshepherd_sara.poo_registry_commit import (
    POO_APPROVAL_INTENT,
    POO_DURABLE_COMMIT_REQUEST_SCHEMA,
    POO_TECHNICAL_REGISTRY_KEY,
)


def bootstrap_body():
    coc = COCEvidence(
        asset_id="asset:api",
        claimant_id="claimant:api",
        control_key_fingerprint="key:api",
        custody_reference="custody:api",
        custody_point_reference="point:api",
        challenge_reference="challenge:api",
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
        asset_id="asset:api",
        claimant_id="claimant:api",
        title_reference="title:api",
        control_key_fingerprint="key:api",
        work_reference="work:api",
        concept_reference="concept:api",
        coc_reference=evaluate_coc(coc).digest,
        stake_reference="stake:api",
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
    projection = bootstrap_commit_readiness_audit_projection(decision, asset_id="asset:api")
    assert decision.commit_decision is not None
    return {
        "schema": POO_DURABLE_COMMIT_REQUEST_SCHEMA,
        "governance_projection": projection,
        "candidate_states": [asdict(state) for state in decision.commit_decision.candidate_states],
        "approval_intent": POO_APPROVAL_INTENT,
        "approval_reference": "approval:api:bootstrap:001",
    }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_bootstrap_is_permanently_closed_after_genesis(client, tokens):
    _relay, admin = tokens
    first = bootstrap_body()
    assert client.post("/admin/poo/registry/commit", json=first, headers=auth(admin)).status_code == 200

    second = bootstrap_body()
    second["approval_reference"] = "approval:api:bootstrap:002"
    response = client.post("/admin/poo/registry/commit", json=second, headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["commit"]["status"] == "ALREADY_COMMITTED"

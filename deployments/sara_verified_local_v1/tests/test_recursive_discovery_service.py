from __future__ import annotations

import json
import stat

import pytest

from worldshepherd_sara.recursive_discovery import (
    DiscoveryKind,
    ExpansionProposal,
    initialize_state,
    make_seed,
    run_recursive_cycle,
    state_digest,
)
from worldshepherd_sara.recursive_discovery_storage import OmegaStateStore
from worldshepherd_sara.storage import DurableStore


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed_payload(statement: str = "Explore a governed recursive frontier.") -> dict[str, object]:
    return {
        "kind": "DOMAIN",
        "domain": "Worldshepherd integration",
        "statement": statement,
        "confidence": 0.0,
        "evidence_state": "UNVERIFIED",
        "cross_domain_tags": ["SARA", "ECHO"],
        "falsification_tests": ["attempt the cheapest useful disconfirming test"],
    }


def test_omega_admin_endpoints_are_fail_closed_for_relay_role(client, tokens):
    relay, _ = tokens
    for method, path, body in [
        ("get", "/admin/omega/status", None),
        ("get", "/admin/omega/frontier", None),
        ("post", "/admin/omega/init", {"seeds": [seed_payload()]}),
        ("post", "/admin/omega/cycle", {"proposals": []}),
    ]:
        response = client.request(method, path, headers=auth(relay), json=body)
        assert response.status_code == 403


def test_omega_initializes_persists_and_exposes_bounded_status(client, tokens):
    _, admin = tokens
    before = client.get("/admin/omega/status", headers=auth(admin))
    assert before.status_code == 200
    assert before.json()["status"]["initialized"] is False
    assert before.json()["status"]["global_depth_limit"] is None
    assert before.json()["status"]["physical_infinity_claimed"] is False
    assert before.json()["status"]["claim_promotion_allowed"] is False
    assert before.json()["status"]["external_execution_allowed"] is False

    response = client.post(
        "/admin/omega/init",
        headers=auth(admin),
        json={"seeds": [seed_payload()], "max_active_frontier": 8},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["initialized"] is True
    assert body["cycle_index"] == 0
    assert body["frontier_count"] == 1
    assert body["claim_promotion_performed"] is False
    assert body["external_execution_performed"] is False

    path = client.app.state.omega_store.path
    assert path.exists()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    frontier = client.get("/admin/omega/frontier", headers=auth(admin))
    assert frontier.status_code == 200
    assert frontier.json()["initialized"] is True
    assert len(frontier.json()["nodes"]) == 1
    assert frontier.json()["nodes"][0]["priority_score"] >= 0.0

    audit = client.get("/v1/audit?limit=50", headers=auth(admin))
    assert any(item["event"] == "omega_initialized" for item in audit.json()["records"])


def test_omega_cycle_advances_state_without_claim_or_external_execution(client, tokens):
    _, admin = tokens
    init = client.post(
        "/admin/omega/init",
        headers=auth(admin),
        json={"seeds": [seed_payload()]},
    )
    assert init.status_code == 200
    frontier = client.get("/admin/omega/frontier", headers=auth(admin)).json()
    parent_id = frontier["nodes"][0]["node_id"]

    response = client.post(
        "/admin/omega/cycle",
        headers=auth(admin),
        json={
            "proposals": [
                {
                    "parent_node_id": parent_id,
                    "kind": "CONTRADICTION",
                    "domain": "Worldshepherd self-audit",
                    "statement": "Search for evidence that contradicts the current assumption.",
                    "confidence": 0.5,
                    "evidence_state": "HYPOTHESIS",
                    "cross_domain_tags": ["red-team"],
                    "falsification_tests": ["run an independent contradiction check"],
                }
            ],
            "policy": {
                "parent_budget_per_cycle": 1,
                "max_children_per_parent": 1,
                "max_new_nodes_per_cycle": 1,
                "max_active_frontier": 8
            },
        },
    )
    assert response.status_code == 200
    report = response.json()["report"]
    assert report["cycle_index"] == 1
    assert len(report["processed_parent_ids"]) == 1
    assert len(report["generated_node_ids"]) == 1
    assert report["global_depth_limit"] is None
    assert report["physical_infinity_claimed"] is False
    assert report["claim_promotion_performed"] is False
    assert report["external_execution_performed"] is False

    status = client.get("/admin/omega/status", headers=auth(admin)).json()["status"]
    assert status["cycle_index"] == 1
    assert status["deepest_live_depth"] == 1

    audit = client.get("/v1/audit?limit=50", headers=auth(admin))
    events = audit.json()["records"]
    assert any(item["event"] == "omega_cycle_completed" for item in events)


def test_omega_rejects_reinitialization_with_different_state(client, tokens):
    _, admin = tokens
    first = client.post(
        "/admin/omega/init",
        headers=auth(admin),
        json={"seeds": [seed_payload("First seed")]},
    )
    assert first.status_code == 200
    second = client.post(
        "/admin/omega/init",
        headers=auth(admin),
        json={"seeds": [seed_payload("Different seed")]},
    )
    assert second.status_code == 409
    assert "already initialized" in second.json()["detail"]


def test_omega_cycle_requires_initialization(client, tokens):
    _, admin = tokens
    response = client.post(
        "/admin/omega/cycle",
        headers=auth(admin),
        json={"proposals": []},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "WS-OMEGA state is not initialized"


def test_omega_state_store_enforces_digest_chain(tmp_path):
    durable = DurableStore(tmp_path)
    custody = OmegaStateStore(durable)
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="custody",
        statement="Verify chained persistence.",
    )
    state = initialize_state([seed])
    custody.initialize(state)
    proposal = ExpansionProposal(
        parent_node_id=seed.node_id,
        kind=DiscoveryKind.HYPOTHESIS,
        domain="custody child",
        statement="Advance one digest-bound cycle.",
    )
    next_state, _ = run_recursive_cycle(state, [proposal])

    with pytest.raises(ValueError, match="state changed"):
        custody.replace(
            expected_state_digest="sha256:" + "0" * 64,
            next_state=next_state,
        )

    custody.replace(
        expected_state_digest=state_digest(state),
        next_state=next_state,
    )
    assert state_digest(custody.load()) == state_digest(next_state)


def test_omega_state_store_detects_tampered_snapshot(tmp_path):
    durable = DurableStore(tmp_path)
    custody = OmegaStateStore(durable)
    seed = make_seed(
        kind=DiscoveryKind.DOMAIN,
        domain="tamper detection",
        statement="Detect a modified persisted frontier.",
    )
    custody.initialize(initialize_state([seed]))
    payload = json.loads(custody.path.read_text(encoding="utf-8"))
    payload["state"]["cycle_index"] = 999
    custody.path.write_text(json.dumps(payload), encoding="utf-8")
    custody.path.chmod(0o600)

    with pytest.raises(RuntimeError, match="state corruption detected"):
        custody.load()

from __future__ import annotations

import base64

from deployments.sara_verified_local_v1.tests.test_poo_registry_commit_api import (
    auth,
    bootstrap_body,
    prime_authorized_body,
)
from worldshepherd_sara.event_outbox import (
    EVENT_OUTBOX_REGISTRY_KEY,
    queue_event_outbox_patch,
)
from worldshepherd_sara.poo_registry_commit import POO_TECHNICAL_REGISTRY_KEY
from worldshepherd_sara.prime_sentinel_poo_authorization import (
    PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY,
)


def _invalid_but_well_formed_signature() -> str:
    return base64.urlsafe_b64encode(b"x" * 64).rstrip(b"=").decode("ascii")


def test_forged_signature_cannot_claim_exact_already_committed_replay(
    client, tokens, monkeypatch
):
    _relay, admin = tokens
    signed = prime_authorized_body(bootstrap_body(suffix="signed-fingerprint"), monkeypatch)
    first = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(admin),
    )
    assert first.status_code == 200
    assert first.json()["commit"]["status"] == "COMMITTED"

    forged = dict(signed)
    forged["prime_authorization"] = dict(signed["prime_authorization"])
    forged["prime_authorization"]["signature_b64url"] = _invalid_but_well_formed_signature()
    replay = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=forged,
        headers=auth(admin),
    )
    assert replay.status_code == 409
    assert "signed_assertion_sha256" in replay.json()["detail"]

    registry = client.get("/admin/poo/registry", headers=auth(admin)).json()["registry"]
    assert len(registry["states"]) == 1
    assert len(registry["commits"]) == 1
    audit = client.get("/v1/audit?limit=50", headers=auth(admin)).json()["records"]
    assert len([r for r in audit if r.get("event") == "poo_technical_registry_committed"]) == 1
    assert len(
        [r for r in audit if r.get("event") == "prime_sentinel_poo_authorization_consumed"]
    ) == 1


def test_one_remaining_outbox_slot_blocks_entire_signed_commit_transaction(
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
                event="capacity_seed",
                actor="test",
                event_id=f"SARA-EVENT-CAPACITY-{index:02d}",
                payload={"index": index},
            )
            working.update(event_patch)
            patch.update(event_patch)
        return patch, True

    assert store.transact_registry(seed) is True
    before = store.get_registry()
    assert len(before[EVENT_OUTBOX_REGISTRY_KEY]) == 31

    signed = prime_authorized_body(bootstrap_body(suffix="two-event-capacity"), monkeypatch)
    response = client.post(
        "/admin/poo/registry/commit-prime-authorized",
        json=signed,
        headers=auth(admin),
    )
    assert response.status_code == 503

    after = store.get_registry()
    assert POO_TECHNICAL_REGISTRY_KEY not in after
    assert PRIME_SENTINEL_POO_AUTHZ_REGISTRY_KEY not in after
    assert after[EVENT_OUTBOX_REGISTRY_KEY] == before[EVENT_OUTBOX_REGISTRY_KEY]

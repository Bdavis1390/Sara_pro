from __future__ import annotations

from worldshepherd_sara.overwatch_tripwire import (
    OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_generic_admin_patch_cannot_mutate_overwatch_namespace(client, tokens):
    _, admin = tokens
    store = client.app.state.store
    before = store.get_registry()

    response = client.patch(
        "/admin/registry",
        headers=_auth(admin),
        json={
            "values": {
                OVERWATCH_CONTAINMENT_INTENTS_REGISTRY_KEY: {
                    "OBS-FORGED": {"disposition": "CONTINUE"}
                }
            }
        },
    )

    assert response.status_code == 422
    assert "OVERWATCH protected registry namespaces" in response.text
    assert store.get_registry() == before


def test_non_overwatch_registry_patch_remains_available(client, tokens):
    _, admin = tokens

    response = client.patch(
        "/admin/registry",
        headers=_auth(admin),
        json={"values": {"PHASE8A_TEST": {"status": "ok"}}},
    )

    assert response.status_code == 200
    assert response.json()["registry"]["PHASE8A_TEST"] == {"status": "ok"}

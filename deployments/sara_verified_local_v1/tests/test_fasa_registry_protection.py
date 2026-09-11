from __future__ import annotations

from worldshepherd_sara.fasa_approval_lease import FASA_APPROVAL_REGISTRY_KEY


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_generic_registry_patch_cannot_mutate_fasa_approval_namespace(client, tokens):
    _, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers=_auth(admin),
        json={
            "values": {
                FASA_APPROVAL_REGISTRY_KEY: {
                    "forged-authorization": {"status": "VERIFIED"}
                }
            }
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Protected registry namespaces must use their governed APIs"
    )

    registry = client.get("/admin/registry", headers=_auth(admin))
    assert registry.status_code == 200
    assert FASA_APPROVAL_REGISTRY_KEY not in registry.json()["registry"]

    audit = client.get("/v1/audit?limit=50", headers=_auth(admin))
    assert audit.status_code == 200
    rejected = [
        item
        for item in audit.json()["records"]
        if item["event"] == "protected_registry_patch_rejected"
    ]
    assert rejected
    assert FASA_APPROVAL_REGISTRY_KEY in rejected[-1]["payload"]["keys"]

from __future__ import annotations

from worldshepherd_sara.discord_event_projection import DISCORD_RECEIPTS_REGISTRY_KEY


def test_discord_receipt_namespace_is_protected_from_generic_admin_patch(client, tokens):
    _, admin = tokens
    response = client.patch(
        "/admin/registry",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "values": {
                DISCORD_RECEIPTS_REGISTRY_KEY: {
                    "schema": "WS-SARA-DISCORD-NOTIFICATION-RECEIPTS-V1",
                    "receipts": {},
                }
            }
        },
    )

    assert response.status_code == 403
    assert DISCORD_RECEIPTS_REGISTRY_KEY not in client.app.state.store.get_registry()

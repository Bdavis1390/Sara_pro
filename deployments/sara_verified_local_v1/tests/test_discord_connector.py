from __future__ import annotations

import json

import pytest

from worldshepherd_sara.discord_connector import DiscordConnector
from worldshepherd_sara.discord_webhook import (
    DISCORD_WEBHOOK_ENV,
    DiscordNotification,
    DiscordWebhookError,
)


VALID_WEBHOOK = "https://discord.com/api/webhooks/123456789012345678/test_token_ABC-123"


def notification() -> DiscordNotification:
    return DiscordNotification(
        event_class="WORKFLOW_STATUS",
        title="Connector validation",
        summary="Bounded Discord connector test message",
        status="READY_FOR_CONTROLLED_TEST",
        priority="P2",
        source_event_id="SARA-EVENT-CONNECTOR-001",
        evidence_ref="TEST-DISCORD-CONNECTOR",
    )


def test_status_reports_unconfigured_without_secret_material():
    connector = DiscordConnector(environment={})
    status = connector.status().to_dict()

    assert status["state"] == "UNCONFIGURED"
    assert status["configured"] is False
    assert status["configuration_valid"] is False
    assert status["endpoint_host"] is None
    assert status["live_delivery_claimed"] is False
    assert status["inbound_read_enabled"] is False
    assert status["inbound_commands_enabled"] is False
    assert DISCORD_WEBHOOK_ENV in status["reason"]


def test_status_validates_and_redacts_configured_webhook():
    connector = DiscordConnector(environment={DISCORD_WEBHOOK_ENV: VALID_WEBHOOK})
    status = connector.status().to_dict()
    rendered = json.dumps(status, sort_keys=True)

    assert status["state"] == "CONFIGURED"
    assert status["configured"] is True
    assert status["configuration_valid"] is True
    assert status["endpoint_host"] == "discord.com"
    assert "test_token_ABC-123" not in rendered
    assert "/api/webhooks/" not in rendered


def test_status_rejects_non_discord_destination_without_echoing_value():
    bad = "https://example.com/api/webhooks/123456789012345678/test_token_ABC-123"
    connector = DiscordConnector(environment={DISCORD_WEBHOOK_ENV: bad})
    status = connector.status().to_dict()
    rendered = json.dumps(status, sort_keys=True)

    assert status["state"] == "INVALID_CONFIGURATION"
    assert status["configured"] is True
    assert status["configuration_valid"] is False
    assert status["endpoint_host"] is None
    assert "example.com" not in rendered
    assert "test_token_ABC-123" not in rendered


def test_dry_run_does_not_require_webhook_configuration():
    connector = DiscordConnector(environment={})
    result = connector.notify(notification(), dry_run=True)

    assert result.dry_run is True
    assert result.delivered is False
    assert result.attempts == 0
    assert result.http_status is None
    assert len(result.content_sha256) == 64


def test_live_notify_requires_safe_configuration():
    connector = DiscordConnector(environment={})

    with pytest.raises(DiscordWebhookError, match="not safely configured"):
        connector.notify(notification())


def test_live_notify_delegates_to_bounded_webhook_transport():
    calls: list[tuple[str, dict, float]] = []

    def transport(url: str, payload: dict, timeout: float):
        calls.append((url, payload, timeout))
        return 204, {}

    connector = DiscordConnector(
        environment={DISCORD_WEBHOOK_ENV: VALID_WEBHOOK},
        transport=transport,
    )
    result = connector.notify(notification())

    assert result.delivered is True
    assert result.dry_run is False
    assert result.http_status == 204
    assert result.attempts == 1
    assert calls[0][0] == VALID_WEBHOOK
    assert calls[0][1]["allowed_mentions"] == {"parse": []}


def test_capabilities_are_outbound_only_and_non_authoritative():
    capabilities = DiscordConnector(environment={}).capabilities()

    assert capabilities["outbound_notifications"] is True
    assert capabilities["dry_run"] is True
    assert capabilities["inbound_read"] is False
    assert capabilities["inbound_commands"] is False
    assert capabilities["claim_mutation"] is False
    assert capabilities["approval_authority"] is False
    assert capabilities["evidence_acceptance"] is False
    assert capabilities["partner_commitment_authority"] is False

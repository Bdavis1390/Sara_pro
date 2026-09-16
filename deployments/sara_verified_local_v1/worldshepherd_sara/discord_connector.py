from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Any, Mapping
from urllib.parse import urlsplit

from .discord_webhook import (
    DISCORD_WEBHOOK_ENV,
    DiscordDeliveryResult,
    DiscordNotification,
    DiscordWebhookError,
    Sleeper,
    Transport,
    _post_json,
    deliver_discord_notification,
    validate_discord_webhook_url,
)


CONNECTOR_ID = "worldshepherd.discord.outbound.v1"
CONNECTOR_MODE = "OUTBOUND_WEBHOOK"
CONNECTOR_AUTHORITY = "NOTIFICATION_ONLY"


@dataclass(frozen=True)
class DiscordConnectorStatus:
    connector_id: str
    mode: str
    authority: str
    state: str
    configured: bool
    configuration_valid: bool
    endpoint_host: str | None
    live_delivery_claimed: bool
    inbound_read_enabled: bool
    inbound_commands_enabled: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiscordConnector:
    """Least-privilege application connector for Discord notifications.

    The connector intentionally wraps the outbound webhook publisher rather than
    creating a Discord bot. It reports configuration health without exposing the
    credential-bearing webhook URL and has no inbound read/command authority.
    """

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        transport: Transport = _post_json,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._environment = environment if environment is not None else os.environ
        self._transport = transport
        self._sleeper = sleeper

    def status(self) -> DiscordConnectorStatus:
        raw = self._environment.get(DISCORD_WEBHOOK_ENV)
        if not raw:
            return DiscordConnectorStatus(
                connector_id=CONNECTOR_ID,
                mode=CONNECTOR_MODE,
                authority=CONNECTOR_AUTHORITY,
                state="UNCONFIGURED",
                configured=False,
                configuration_valid=False,
                endpoint_host=None,
                live_delivery_claimed=False,
                inbound_read_enabled=False,
                inbound_commands_enabled=False,
                reason=f"{DISCORD_WEBHOOK_ENV} is not set",
            )

        try:
            canonical = validate_discord_webhook_url(raw)
        except DiscordWebhookError as exc:
            return DiscordConnectorStatus(
                connector_id=CONNECTOR_ID,
                mode=CONNECTOR_MODE,
                authority=CONNECTOR_AUTHORITY,
                state="INVALID_CONFIGURATION",
                configured=True,
                configuration_valid=False,
                endpoint_host=None,
                live_delivery_claimed=False,
                inbound_read_enabled=False,
                inbound_commands_enabled=False,
                reason=str(exc),
            )

        return DiscordConnectorStatus(
            connector_id=CONNECTOR_ID,
            mode=CONNECTOR_MODE,
            authority=CONNECTOR_AUTHORITY,
            state="CONFIGURED",
            configured=True,
            configuration_valid=True,
            endpoint_host=urlsplit(canonical).hostname,
            live_delivery_claimed=False,
            inbound_read_enabled=False,
            inbound_commands_enabled=False,
            reason=None,
        )

    def capabilities(self) -> dict[str, Any]:
        return {
            "connector_id": CONNECTOR_ID,
            "mode": CONNECTOR_MODE,
            "authority": CONNECTOR_AUTHORITY,
            "outbound_notifications": True,
            "dry_run": True,
            "inbound_read": False,
            "inbound_commands": False,
            "claim_mutation": False,
            "approval_authority": False,
            "evidence_acceptance": False,
            "partner_commitment_authority": False,
        }

    def notify(
        self,
        notification: DiscordNotification,
        *,
        dry_run: bool = False,
        timeout_seconds: float = 5.0,
        max_attempts: int = 3,
    ) -> DiscordDeliveryResult:
        webhook_url = self._environment.get(DISCORD_WEBHOOK_ENV)
        if not dry_run:
            status = self.status()
            if not status.configuration_valid:
                raise DiscordWebhookError(
                    "Discord connector is not safely configured for live delivery"
                )

        kwargs: dict[str, Any] = {
            "webhook_url": webhook_url,
            "dry_run": dry_run,
            "timeout_seconds": timeout_seconds,
            "max_attempts": max_attempts,
            "transport": self._transport,
        }
        if self._sleeper is not None:
            kwargs["sleeper"] = self._sleeper
        return deliver_discord_notification(notification, **kwargs)


def connector_status() -> dict[str, Any]:
    """Return redacted connector health for diagnostics and automation."""
    return DiscordConnector().status().to_dict()


def main(argv: list[str] | None = None) -> int:
    del argv
    status = DiscordConnector().status()
    print(json.dumps(status.to_dict(), indent=2, sort_keys=True))
    return 0 if status.configuration_valid else 3


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import pytest

from worldshepherd_sara.discord_webhook import (
    DiscordNotification,
    DiscordWebhookError,
    build_discord_payload,
    deliver_discord_notification,
    render_discord_notification,
    validate_discord_webhook_url,
)


VALID_WEBHOOK = "https://discord.com/api/webhooks/1234567890/AbCdEf_123-token"


def notice(**overrides):
    values = {
        "event_class": "WORKFLOW_STATUS",
        "title": "PR validation complete",
        "summary": "Required checks completed successfully.",
        "status": "VALIDATED",
        "priority": "P1",
        "source_event_id": "SARA-EVENT-TEST-001",
        "evidence_ref": "PR-311",
        "source_url": "https://github.com/Bdavis1390/Sara_pro/pull/311",
    }
    values.update(overrides)
    return DiscordNotification(**values)


def test_webhook_url_is_restricted_and_canonicalized():
    assert validate_discord_webhook_url(VALID_WEBHOOK + "?wait=true#ignored") == VALID_WEBHOOK

    with pytest.raises(DiscordWebhookError, match="host is not allowed"):
        validate_discord_webhook_url(
            "https://example.com/api/webhooks/1234567890/AbCdEf_123-token"
        )
    with pytest.raises(DiscordWebhookError, match="must use HTTPS"):
        validate_discord_webhook_url(
            "http://discord.com/api/webhooks/1234567890/AbCdEf_123-token"
        )


def test_render_neutralizes_mentions_and_disables_allowed_mentions():
    rendered = render_discord_notification(
        notice(summary="Review requested from @everyone and @CRE1AWS")
    )
    assert "@everyone" not in rendered
    assert "@\u200beveryone" in rendered
    payload = build_discord_payload(notice(summary="No notification ping"))
    assert payload["allowed_mentions"] == {"parse": []}


def test_sensitive_material_is_rejected_before_delivery():
    with pytest.raises(DiscordWebhookError, match="credential material"):
        render_discord_notification(notice(summary="api_key=DO-NOT-SEND-123456"))
    with pytest.raises(DiscordWebhookError, match="credential material"):
        render_discord_notification(
            notice(summary="https://discord.com/api/webhooks/1234567890/secret-token")
        )


def test_event_class_and_priority_are_allowlisted():
    with pytest.raises(DiscordWebhookError, match="event_class is not permitted"):
        render_discord_notification(notice(event_class="EXECUTE_COMMAND"))
    with pytest.raises(DiscordWebhookError, match="priority must be"):
        render_discord_notification(notice(priority="P-ROOT"))


def test_oversized_message_fails_closed():
    with pytest.raises(DiscordWebhookError, match="exceeds 2000"):
        render_discord_notification(notice(summary="x" * 2100))


def test_dry_run_never_calls_transport():
    called = False

    def transport(_url, _payload, _timeout):
        nonlocal called
        called = True
        return 204, {}

    result = deliver_discord_notification(
        notice(), dry_run=True, transport=transport
    )
    assert result.dry_run is True
    assert result.delivered is False
    assert result.attempts == 0
    assert result.http_status is None
    assert len(result.content_sha256) == 64
    assert called is False


def test_rate_limit_retries_without_exposing_webhook():
    responses = iter([(429, {"Retry-After": "0"}), (204, {})])
    calls = []
    sleeps = []

    def transport(url, payload, timeout):
        calls.append((url, payload, timeout))
        return next(responses)

    result = deliver_discord_notification(
        notice(),
        webhook_url=VALID_WEBHOOK,
        transport=transport,
        sleeper=sleeps.append,
    )
    assert result.delivered is True
    assert result.attempts == 2
    assert result.http_status == 204
    assert calls[0][0] == VALID_WEBHOOK
    assert calls[0][1]["allowed_mentions"] == {"parse": []}
    assert sleeps == [0.0]


def test_non_retryable_failure_stops_immediately():
    calls = 0

    def transport(_url, _payload, _timeout):
        nonlocal calls
        calls += 1
        return 403, {}

    with pytest.raises(DiscordWebhookError, match="HTTP status 403"):
        deliver_discord_notification(
            notice(),
            webhook_url=VALID_WEBHOOK,
            transport=transport,
            sleeper=lambda _seconds: None,
        )
    assert calls == 1


def test_retry_budget_is_bounded():
    calls = 0

    def transport(_url, _payload, _timeout):
        nonlocal calls
        calls += 1
        return 503, {}

    with pytest.raises(DiscordWebhookError, match="HTTP status 503"):
        deliver_discord_notification(
            notice(),
            webhook_url=VALID_WEBHOOK,
            max_attempts=3,
            transport=transport,
            sleeper=lambda _seconds: None,
        )
    assert calls == 3

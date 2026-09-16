from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


DISCORD_WEBHOOK_ENV = "WORLDSHEPHERD_DISCORD_WEBHOOK_URL"
MAX_DISCORD_CONTENT_CHARS = 2000
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_ATTEMPTS = 3
_ALLOWED_WEBHOOK_HOSTS = frozenset({"discord.com", "discordapp.com"})
_ALLOWED_EVENT_CLASSES = frozenset(
    {
        "APPROVAL_REQUIRED",
        "EVIDENCE_STATUS",
        "OPPORTUNITY_STATUS",
        "OUTREACH_STATUS",
        "SYSTEM_ALERT",
        "WORKFLOW_STATUS",
    }
)
_VALID_PRIORITIES = frozenset({"P0", "P1", "P2", "P3"})
_WEBHOOK_PATH = re.compile(r"^/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9._-]+$")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)\b(?:authorization|bearer|password|passwd|api[_-]?key|secret|"
    r"webhook[_-]?url|token)\b\s*[:=]\s*\S+"
)
_SECRET_TOKEN = re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{10,}\b")
_DISCORD_WEBHOOK_IN_TEXT = re.compile(r"(?i)/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9._-]+")


class DiscordWebhookError(ValueError):
    """Raised when a Discord notification cannot be safely rendered or delivered."""


@dataclass(frozen=True)
class DiscordNotification:
    event_class: str
    title: str
    summary: str
    status: str
    priority: str = "P2"
    source_event_id: str | None = None
    evidence_ref: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class DiscordDeliveryResult:
    delivered: bool
    dry_run: bool
    attempts: int
    http_status: int | None
    content_sha256: str
    delivered_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Transport = Callable[[str, dict[str, Any], float], tuple[int, Mapping[str, str]]]
Sleeper = Callable[[float], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_discord_webhook_url(value: str) -> str:
    """Validate and canonicalize an official Discord incoming-webhook URL.

    The credential-bearing webhook URL is deliberately never returned in an
    error message. Queries/fragments are stripped so callers cannot smuggle
    alternate delivery behavior into configuration.
    """
    if not isinstance(value, str) or not value.strip():
        raise DiscordWebhookError("Discord webhook URL is required")
    parsed = urlsplit(value.strip())
    try:
        port = parsed.port
    except ValueError as exc:
        raise DiscordWebhookError("Discord webhook URL has an invalid port") from exc
    if parsed.scheme != "https":
        raise DiscordWebhookError("Discord webhook URL must use HTTPS")
    if parsed.username or parsed.password:
        raise DiscordWebhookError("Discord webhook URL must not contain user info")
    if parsed.hostname not in _ALLOWED_WEBHOOK_HOSTS:
        raise DiscordWebhookError("Discord webhook URL host is not allowed")
    if port not in (None, 443):
        raise DiscordWebhookError("Discord webhook URL must use the default HTTPS port")
    if not _WEBHOOK_PATH.fullmatch(parsed.path):
        raise DiscordWebhookError("Discord webhook URL path is not a valid incoming webhook")
    return urlunsplit(("https", parsed.hostname, parsed.path, "", ""))


def _reject_sensitive_text(value: str, *, field: str) -> None:
    if (
        _SENSITIVE_ASSIGNMENT.search(value)
        or _SECRET_TOKEN.search(value)
        or _DISCORD_WEBHOOK_IN_TEXT.search(value)
    ):
        raise DiscordWebhookError(f"{field} appears to contain credential material")


def _clean_text(value: str | None, *, field: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise DiscordWebhookError(f"{field} is required")
        return None
    if not isinstance(value, str):
        raise DiscordWebhookError(f"{field} must be text")
    cleaned = value.strip()
    if required and not cleaned:
        raise DiscordWebhookError(f"{field} is required")
    if not cleaned:
        return None
    _reject_sensitive_text(cleaned, field=field)
    # Discord also receives allowed_mentions.parse=[], but neutralizing '@'
    # here provides defense in depth if the rendering is later reused.
    return cleaned.replace("@", "@\u200b")


def _clean_source_url(value: str | None) -> str | None:
    cleaned = _clean_text(value, field="source_url")
    if cleaned is None:
        return None
    parsed = urlsplit(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise DiscordWebhookError("source_url must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise DiscordWebhookError("source_url must not contain user info")
    return cleaned


def render_discord_notification(notification: DiscordNotification) -> str:
    event_class = _clean_text(notification.event_class, field="event_class", required=True)
    assert event_class is not None
    if event_class not in _ALLOWED_EVENT_CLASSES:
        raise DiscordWebhookError("event_class is not permitted for Discord delivery")

    priority = _clean_text(notification.priority, field="priority", required=True)
    assert priority is not None
    if priority not in _VALID_PRIORITIES:
        raise DiscordWebhookError("priority must be one of P0, P1, P2, or P3")

    title = _clean_text(notification.title, field="title", required=True)
    summary = _clean_text(notification.summary, field="summary", required=True)
    status = _clean_text(notification.status, field="status", required=True)
    source_event_id = _clean_text(notification.source_event_id, field="source_event_id")
    evidence_ref = _clean_text(notification.evidence_ref, field="evidence_ref")
    source_url = _clean_source_url(notification.source_url)
    assert title is not None and summary is not None and status is not None

    lines = [
        f"**[WORLDSHEPHERD][{event_class}][{priority}] {title}**",
        f"Status: `{status}`",
        summary,
    ]
    if source_event_id:
        lines.append(f"Event: `{source_event_id}`")
    if evidence_ref:
        lines.append(f"Evidence: `{evidence_ref}`")
    if source_url:
        lines.append(f"Source: {source_url}")

    content = "\n".join(lines)
    if len(content) > MAX_DISCORD_CONTENT_CHARS:
        raise DiscordWebhookError(
            f"rendered Discord message exceeds {MAX_DISCORD_CONTENT_CHARS} characters"
        )
    return content


def build_discord_payload(notification: DiscordNotification) -> dict[str, Any]:
    return {
        "content": render_discord_notification(notification),
        "allowed_mentions": {"parse": []},
    }


def _post_json(
    webhook_url: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[int, Mapping[str, str]]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    request = Request(
        webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Worldshepherd-SARA/discord-webhook-v1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status), dict(response.headers.items())
    except HTTPError as exc:
        # Return only the status and headers. Discord response bodies can contain
        # remote text we do not need to persist or echo into logs.
        return int(exc.code), dict(exc.headers.items()) if exc.headers else {}
    except URLError as exc:
        raise DiscordWebhookError("Discord delivery failed due to a network error") from None


def _retry_delay(headers: Mapping[str, str]) -> float:
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return 0.5
    try:
        return min(max(float(raw), 0.0), 10.0)
    except (TypeError, ValueError):
        return 0.5


def deliver_discord_notification(
    notification: DiscordNotification,
    *,
    webhook_url: str | None = None,
    dry_run: bool = False,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    transport: Transport = _post_json,
    sleeper: Sleeper = time.sleep,
) -> DiscordDeliveryResult:
    """Render and optionally deliver one bounded Worldshepherd notification.

    This function has no authority to mutate SARA claim state, approval state,
    engineering state, or audit records. ``source_event_id`` is correspondence
    metadata only; the durable SARA/GitHub record remains authoritative.
    """
    if timeout_seconds <= 0:
        raise DiscordWebhookError("timeout_seconds must be greater than zero")
    if max_attempts < 1 or max_attempts > 5:
        raise DiscordWebhookError("max_attempts must be between 1 and 5")

    payload = build_discord_payload(notification)
    fingerprint = hashlib.sha256(payload["content"].encode("utf-8")).hexdigest()
    if dry_run:
        return DiscordDeliveryResult(
            delivered=False,
            dry_run=True,
            attempts=0,
            http_status=None,
            content_sha256=fingerprint,
            delivered_at=None,
        )

    canonical_url = validate_discord_webhook_url(webhook_url or "")
    last_status: int | None = None
    for attempt in range(1, max_attempts + 1):
        status, headers = transport(canonical_url, payload, timeout_seconds)
        last_status = status
        if 200 <= status < 300:
            return DiscordDeliveryResult(
                delivered=True,
                dry_run=False,
                attempts=attempt,
                http_status=status,
                content_sha256=fingerprint,
                delivered_at=_utc_now(),
            )
        retryable = status == 429 or status >= 500
        if retryable and attempt < max_attempts:
            sleeper(_retry_delay(headers))
            continue
        raise DiscordWebhookError(f"Discord delivery failed with HTTP status {status}")

    raise DiscordWebhookError(
        f"Discord delivery failed after {max_attempts} attempts; last status {last_status}"
    )

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
import sys
from typing import Any

from .discord_connector import DiscordConnector, DiscordConnectorError
from .discord_webhook import DiscordNotification, DiscordWebhookError
from .event_outbox import EVENT_OUTBOX_REGISTRY_KEY, EventOutboxError, outbox_status
from .storage import DurableStore


DISCORD_RECEIPTS_REGISTRY_KEY = "SARA_DISCORD_NOTIFICATION_RECEIPTS"
DISCORD_RECEIPTS_SCHEMA = "WS-SARA-DISCORD-NOTIFICATION-RECEIPTS-V1"
MAX_DISCORD_RECEIPTS = 32
AUDIT_CONFIRMATION_LOOKBACK = 8192

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SAFE_STATE = re.compile(r"^[A-Z0-9_:-]{1,128}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


class DiscordEventProjectionError(RuntimeError):
    """Raised when post-audit Discord projection cannot proceed safely."""


@dataclass(frozen=True)
class DiscordProjectionRecord:
    event_id: str
    event: str
    dry_run: bool
    delivered: bool
    receipt_written: bool
    content_sha256: str


@dataclass(frozen=True)
class DiscordProjectionBatchResult:
    dry_run: bool
    scanned_delivered: int
    mapped: int
    already_receipted: int
    unmapped: int
    projected: int
    receipts_written: int
    results: tuple[DiscordProjectionRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["results"] = [asdict(item) for item in self.results]
        return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _safe_identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise DiscordEventProjectionError(f"{field} is not a safe bounded identifier")
    return value


def _safe_state(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_STATE.fullmatch(value):
        raise DiscordEventProjectionError(f"{field} is not a safe bounded state")
    return value


def _receipt_state(registry: dict[str, Any]) -> dict[str, dict[str, str]]:
    raw = registry.get(DISCORD_RECEIPTS_REGISTRY_KEY)
    if raw is None:
        return {}
    if not isinstance(raw, dict) or raw.get("schema") != DISCORD_RECEIPTS_SCHEMA:
        raise DiscordEventProjectionError("Discord receipt registry is malformed")
    receipts = raw.get("receipts")
    if not isinstance(receipts, dict) or len(receipts) > MAX_DISCORD_RECEIPTS:
        raise DiscordEventProjectionError("Discord receipt registry is malformed")

    validated: dict[str, dict[str, str]] = {}
    for event_id, receipt in receipts.items():
        if not isinstance(receipt, dict):
            raise DiscordEventProjectionError("Discord receipt registry is malformed")
        if receipt.get("event_id") != event_id:
            raise DiscordEventProjectionError("Discord receipt registry is malformed")
        event = receipt.get("event")
        digest = receipt.get("content_sha256")
        notified_at = receipt.get("notified_at")
        if (
            not isinstance(event_id, str)
            or not _SAFE_ID.fullmatch(event_id)
            or not isinstance(event, str)
            or not event
            or not isinstance(digest, str)
            or not _SHA256.fullmatch(digest)
            or not _valid_timestamp(notified_at)
        ):
            raise DiscordEventProjectionError("Discord receipt registry is malformed")
        validated[event_id] = {
            "event_id": event_id,
            "event": event,
            "content_sha256": digest,
            "notified_at": str(notified_at),
        }
    return validated


def _receipt_patch(
    registry: dict[str, Any],
    *,
    event_id: str,
    event: str,
    content_sha256: str,
    notified_at: str,
) -> tuple[dict[str, Any] | None, bool]:
    receipts = _receipt_state(registry)
    if event_id in receipts:
        return None, False
    receipts[event_id] = {
        "event_id": event_id,
        "event": event,
        "content_sha256": content_sha256,
        "notified_at": notified_at,
    }
    if len(receipts) > MAX_DISCORD_RECEIPTS:
        ordered = sorted(
            receipts.items(),
            key=lambda item: (item[1]["notified_at"], item[0]),
        )
        for key, _value in ordered[: len(receipts) - MAX_DISCORD_RECEIPTS]:
            receipts.pop(key, None)
    return {
        DISCORD_RECEIPTS_REGISTRY_KEY: {
            "schema": DISCORD_RECEIPTS_SCHEMA,
            "receipts": receipts,
        }
    }, True


def _audit_confirmation_ids(store: DurableStore) -> dict[str, str]:
    confirmed: dict[str, str] = {}
    for record in store.read_audit(AUDIT_CONFIRMATION_LOOKBACK):
        event = record.get("event")
        payload = record.get("payload")
        if not isinstance(event, str) or not isinstance(payload, dict):
            continue
        event_id = payload.get("_outbox_event_id")
        semantics = payload.get("_delivery_semantics")
        if (
            isinstance(event_id, str)
            and event_id
            and semantics == "AT_LEAST_ONCE"
        ):
            confirmed[event_id] = event
    return confirmed


def _project_custody(event_id: str, payload: dict[str, Any]) -> DiscordNotification:
    if payload.get("schema") != "WS-ECHO-PRIME-CUSTODY-V1":
        raise DiscordEventProjectionError("PRIME custody event has an unexpected schema")
    prime_id = _safe_identifier(payload.get("prime_id"), field="prime_id")
    transition_id = _safe_identifier(payload.get("transition_id"), field="transition_id")
    action = _safe_state(payload.get("action"), field="action")
    previous_state = _safe_state(payload.get("previous_state"), field="previous_state")
    new_state = _safe_state(payload.get("new_state"), field="new_state")
    return DiscordNotification(
        event_class="EVIDENCE_STATUS",
        title=f"PRIME custody: {action}",
        summary=(
            f"{prime_id}: {previous_state} -> {new_state}. "
            "Review the durable SARA/ECHO record for evidence and details."
        ),
        status=new_state,
        priority="P2",
        source_event_id=event_id,
        evidence_ref=transition_id,
    )


def _project_authorization_rejection(
    event_id: str,
    payload: dict[str, Any],
) -> DiscordNotification:
    prime_id = _safe_identifier(payload.get("prime_id"), field="prime_id")
    return DiscordNotification(
        event_class="SYSTEM_ALERT",
        title="PRIME SENTINEL authorization rejected",
        summary=(
            f"{prime_id}: authorization rejected. "
            "Review the durable SARA audit for the reason and authorization context."
        ),
        status="REJECTED",
        priority="P1",
        source_event_id=event_id,
    )


def notification_for_delivered_event(
    event_id: str,
    entry: dict[str, Any],
) -> DiscordNotification | None:
    if entry.get("status") != "DELIVERED":
        return None
    event = entry.get("event")
    payload = entry.get("payload")
    if not isinstance(event, str) or not isinstance(payload, dict):
        raise DiscordEventProjectionError("delivered outbox event is malformed")
    if event == "prime_custody_provenance":
        return _project_custody(event_id, payload)
    if event == "prime_sentinel_authorization_rejected":
        return _project_authorization_rejection(event_id, payload)
    return None


def project_delivered_events(
    store: DurableStore,
    *,
    connector: DiscordConnector | None = None,
    dry_run: bool = False,
    limit: int = 10,
) -> DiscordProjectionBatchResult:
    """Project already-audited SARA outbox events to Discord.

    The authoritative event outbox is never mutated here. Successful live
    delivery is followed by a compact receipt write used only for notification
    deduplication. If delivery succeeds but receipt persistence fails, a later
    run may send the same stable event ID again. This is deliberate at-least-once
    notification behavior; Discord is not an authoritative state store.
    """
    if limit < 1 or limit > 32:
        raise ValueError("limit must be between 1 and 32")

    connector = connector or DiscordConnector()
    registry = store.get_registry()
    try:
        status = outbox_status(registry)
    except EventOutboxError as exc:
        raise DiscordEventProjectionError(str(exc)) from exc
    if status["malformed"]:
        raise DiscordEventProjectionError("event outbox contains malformed records")

    receipts = _receipt_state(registry)
    raw_outbox = registry.get(EVENT_OUTBOX_REGISTRY_KEY, {})
    if not isinstance(raw_outbox, dict):
        raise DiscordEventProjectionError("event outbox is malformed")
    confirmed = _audit_confirmation_ids(store)

    candidates: list[tuple[str, str, dict[str, Any], DiscordNotification]] = []
    already_receipted = 0
    unmapped = 0
    scanned_delivered = 0
    for event_id, entry in raw_outbox.items():
        if not isinstance(entry, dict) or entry.get("status") != "DELIVERED":
            continue
        scanned_delivered += 1
        if event_id in receipts:
            already_receipted += 1
            continue
        notification = notification_for_delivered_event(event_id, entry)
        if notification is None:
            unmapped += 1
            continue
        if confirmed.get(event_id) != entry.get("event"):
            raise DiscordEventProjectionError(
                "mapped delivered event lacks matching recent SARA audit confirmation"
            )
        candidates.append((str(entry.get("delivered_at", "")), event_id, entry, notification))

    candidates.sort(key=lambda item: (item[0], item[1]))
    candidates = candidates[:limit]
    results: list[DiscordProjectionRecord] = []
    receipts_written = 0

    for _delivered_at, event_id, entry, notification in candidates:
        try:
            delivery = connector.notify(notification, dry_run=dry_run)
        except (DiscordConnectorError, DiscordWebhookError, ValueError) as exc:
            raise DiscordEventProjectionError(str(exc)) from exc

        receipt_written = False
        if not dry_run:
            if not delivery.delivered:
                raise DiscordEventProjectionError(
                    "Discord connector returned without confirming live delivery"
                )

            def operation(current: dict[str, Any]):
                return _receipt_patch(
                    current,
                    event_id=event_id,
                    event=str(entry["event"]),
                    content_sha256=delivery.content_sha256,
                    notified_at=delivery.delivered_at or _utc_now(),
                )

            try:
                receipt_written = store.transact_registry(operation)
            except (OSError, RuntimeError, ValueError, DiscordEventProjectionError) as exc:
                raise DiscordEventProjectionError(
                    "Discord delivery succeeded but receipt persistence failed; "
                    "the stable event ID may be replayed"
                ) from exc
            if receipt_written:
                receipts_written += 1

        results.append(
            DiscordProjectionRecord(
                event_id=event_id,
                event=str(entry["event"]),
                dry_run=dry_run,
                delivered=bool(delivery.delivered),
                receipt_written=receipt_written,
                content_sha256=delivery.content_sha256,
            )
        )

    return DiscordProjectionBatchResult(
        dry_run=dry_run,
        scanned_delivered=scanned_delivered,
        mapped=len(candidates),
        already_receipted=already_receipted,
        unmapped=unmapped,
        projected=len(results),
        receipts_written=receipts_written,
        results=tuple(results),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project already-audited SARA events to the outbound Discord connector."
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render eligible projections without network delivery or receipt writes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = project_delivered_events(
            DurableStore(),
            dry_run=args.dry_run,
            limit=args.limit,
        )
    except (DiscordEventProjectionError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

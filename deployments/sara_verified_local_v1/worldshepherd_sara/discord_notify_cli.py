from __future__ import annotations

import argparse
import json
import os
import sys

from .discord_webhook import (
    DISCORD_WEBHOOK_ENV,
    DiscordNotification,
    DiscordWebhookError,
    build_discord_payload,
    deliver_discord_notification,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send a bounded Worldshepherd status notification to Discord."
    )
    parser.add_argument("--event-class", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--priority", default="P2")
    parser.add_argument("--source-event-id")
    parser.add_argument("--evidence-ref")
    parser.add_argument("--source-url")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate without network delivery or webhook configuration.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    notification = DiscordNotification(
        event_class=args.event_class,
        title=args.title,
        summary=args.summary,
        status=args.status,
        priority=args.priority,
        source_event_id=args.source_event_id,
        evidence_ref=args.evidence_ref,
        source_url=args.source_url,
    )
    try:
        result = deliver_discord_notification(
            notification,
            webhook_url=os.environ.get(DISCORD_WEBHOOK_ENV),
            dry_run=args.dry_run,
        )
        output = result.to_dict()
        if args.dry_run:
            # The rendered content has already passed the credential guard and
            # is useful for a human approval check before enabling delivery.
            output["content"] = build_discord_payload(notification)["content"]
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except DiscordWebhookError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

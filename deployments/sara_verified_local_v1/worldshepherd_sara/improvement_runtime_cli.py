from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Sequence

from .improvement_feedback import ImprovementFeedbackPolicy
from .improvement_runtime import ImprovementRuntime, ImprovementRuntimeError


def _json(value: object) -> None:
    print(json.dumps(value, sort_keys=True, indent=2))


def _runtime() -> ImprovementRuntime:
    runtime = ImprovementRuntime.from_environment()
    if runtime is None:
        raise ImprovementRuntimeError("WSRI_DATA_DIR is required")
    return runtime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ws-ri-runtime",
        description="Operator-invoked Worldshepherd recursive-improvement runtime",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show ledger and feedback-cursor status")

    records = sub.add_parser("records", help="export bounded WS-RI custody records")
    records.add_argument("--limit", type=int, default=50)
    records.add_argument("--improvement-id")

    feedback = sub.add_parser("feedback-run", help="run one bounded ECHO feedback cycle")
    feedback.add_argument("--actor", required=True)
    feedback.add_argument("--max-events", type=int, default=64)
    feedback.add_argument("--max-proposals", type=int, default=32)

    checkpoint = sub.add_parser(
        "checkpoint-payload",
        help="emit a ledger checkpoint payload for the governed SARA/ECHO provenance path",
    )
    checkpoint.add_argument("--created-utc")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        runtime = _runtime()
        if args.command == "status":
            _json(runtime.status())
            return 0
        if args.command == "records":
            _json(
                {
                    "records": runtime.export_records(
                        limit=args.limit,
                        improvement_id=args.improvement_id,
                    ),
                    "claims_boundary": "bounded local custody export only",
                }
            )
            return 0
        if args.command == "feedback-run":
            policy = ImprovementFeedbackPolicy(
                max_echo_events_per_cycle=args.max_events,
                max_new_proposals_per_cycle=args.max_proposals,
            )
            report = runtime.run_feedback_once(actor=args.actor, policy=policy)
            _json(
                {
                    "report": report.model_dump(mode="json"),
                    "scheduler_mode": "OPERATOR_INVOKED_SINGLE_BOUNDED_CYCLE",
                }
            )
            return 0
        if args.command == "checkpoint-payload":
            created = args.created_utc or datetime.now(timezone.utc).isoformat()
            _json(runtime.checkpoint_outbox_payload(created_utc=created))
            return 0
    except (ImprovementRuntimeError, OSError, ValueError) as exc:
        parser = build_parser()
        parser.error(str(exc))
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())

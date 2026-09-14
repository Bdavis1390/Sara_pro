#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worldshepherd_sara import ConnectorControlPlane, decision_to_dict

MANIFEST = ROOT / "data" / "worldshepherd_connectors.v2.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run a Worldshepherd connector action against PRIME-style policy."
    )
    parser.add_argument("connector_id")
    parser.add_argument("action")
    parser.add_argument("--actor", default="operator", choices=["operator", "admin"])
    parser.add_argument(
        "--data-class",
        default="PUBLIC",
        choices=["PUBLIC", "INTERNAL", "CONTROLLED_UNCLASSIFIED"],
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Evaluate as an already human-approved proposal. This tool still performs no external action.",
    )
    parser.add_argument("--approval-id", default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    control = ConnectorControlPlane(MANIFEST)
    decision = control.authorize(
        connector_id=args.connector_id,
        action=args.action,
        actor=args.actor,
        data_class=args.data_class,
        human_approved=args.approved,
        approval_id=args.approval_id,
        context={"source": "tools/connector_control/evaluate.py", "dry_run": True},
    )
    print(json.dumps(decision_to_dict(decision), indent=2, sort_keys=True))
    return 0 if decision.allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())

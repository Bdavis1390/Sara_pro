from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit_checkpoint import SaraAuditCheckpointManager
from .audit_checkpoint_anchor import (
    export_external_anchor,
    verify_with_external_anchor,
)
from .audit_checkpoint_guarded import GuardedSaraAuditCheckpointManager
from .storage import DurableStore


def _manager() -> SaraAuditCheckpointManager:
    store = DurableStore()
    return GuardedSaraAuditCheckpointManager.from_environment(store)


def _emit(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m worldshepherd_sara.audit_checkpoint_operator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("create", help="Create and durably append a signed local audit checkpoint")

    verify = sub.add_parser("verify", help="Verify the local signed checkpoint chain and audit prefix")
    verify.add_argument("--expected-latest-sha256")

    export = sub.add_parser(
        "export-anchor",
        help="Export the latest checkpoint pin outside SARA_DATA_DIR",
    )
    export.add_argument("--out", required=True)

    verify_anchor = sub.add_parser(
        "verify-anchor",
        help="Verify local audit/checkpoint state against an externally retained anchor",
    )
    verify_anchor.add_argument("--anchor", required=True)

    sub.add_parser("public-key", help="Print the audit-checkpoint public-key record")

    args = parser.parse_args()
    manager = _manager()

    if args.command == "create":
        _emit(manager.create_checkpoint())
    elif args.command == "verify":
        _emit(
            manager.verify_current(
                expected_latest_checkpoint_sha256=args.expected_latest_sha256
            )
        )
    elif args.command == "export-anchor":
        _emit(export_external_anchor(manager, Path(args.out)))
    elif args.command == "verify-anchor":
        _emit(verify_with_external_anchor(manager, Path(args.anchor)))
    elif args.command == "public-key":
        _emit(manager.public_key_record())
    else:  # pragma: no cover
        raise RuntimeError("unknown audit checkpoint operator command")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

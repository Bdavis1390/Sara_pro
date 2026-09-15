from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worldshepherd_sara.audit_checkpoint_offline_verify import (
    SaraAuditOfflineVerificationError,
    verify_offline_export,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify an exported SARA application audit, signed checkpoint ledger, "
            "and independently retained external anchor without any private signing key."
        )
    )
    parser.add_argument("--audit", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--out")
    args = parser.parse_args()

    try:
        result = verify_offline_export(
            audit_path=Path(args.audit),
            checkpoint_ledger_path=Path(args.ledger),
            external_anchor_path=Path(args.anchor),
        )
    except SaraAuditOfflineVerificationError as exc:
        failure = {
            "schema": "WS-SARA-AUDIT-OFFLINE-VERIFIER-CLI-V1",
            "status": "REJECTED",
            "error": str(exc),
            "private_key_required": False,
            "running_sara_required": False,
        }
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        return 2

    payload = {
        "schema": "WS-SARA-AUDIT-OFFLINE-VERIFIER-CLI-V1",
        **result,
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out:
        output = Path(args.out)
        if not output.is_absolute():
            raise SystemExit("--out path must be absolute")
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

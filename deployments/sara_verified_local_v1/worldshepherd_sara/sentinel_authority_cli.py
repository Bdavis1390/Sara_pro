from __future__ import annotations

import argparse
import json
from pathlib import Path

from .isolated_custody_client import AuthorityUnavailable, CustodyClient

CLAIMS_BOUNDARY = (
    "This command reports isolated Sentinel custody-authority availability and detached state only. "
    "It does not establish Sentinel fitness, government acceptance, supplier status, CMMC/NIST conformity, "
    "clearance, deployment authority, certification, or operational effectiveness."
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fail-closed Sentinel authority status/readiness client."
    )
    parser.add_argument("--authority-socket", required=True)
    parser.add_argument("--package-id")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    client = CustodyClient(args.authority_socket)
    try:
        health = client.health()
        if not health.get("ok"):
            raise AuthorityUnavailable(str(health.get("error") or "authority health failed"))
        result = {
            "schema": "WS-SENTINEL-AUTHORITY-STATUS-V1",
            "authority_status": "READY",
            "authority_schema": health.get("schema"),
            "package_snapshot": None,
            "claims_boundary": CLAIMS_BOUNDARY,
        }
        if args.package_id:
            snapshot = client.get_snapshot(args.package_id)
            if not snapshot.get("ok"):
                raise AuthorityUnavailable(str(snapshot.get("error") or "snapshot unavailable"))
            result["package_snapshot"] = snapshot.get("snapshot")
    except AuthorityUnavailable as exc:
        result = {
            "schema": "WS-SENTINEL-AUTHORITY-STATUS-V1",
            "authority_status": "FAIL_CLOSED",
            "error": str(exc),
            "claims_boundary": CLAIMS_BOUNDARY,
        }
        if args.out:
            args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(2)

    if args.out:
        args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""List ONLINE Amazon Braket QPUs visible to a local AWS profile.

Read-only. This script performs SearchDevices/GetDevice calls only. It never submits a
quantum task and never accepts access-key or secret-key material.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_braket_discovery import candidates_as_dict, discover_online_qpus


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only discovery of ONLINE Amazon Braket QPUs")
    parser.add_argument("--region", required=True, help="AWS region to query, e.g. us-west-1")
    parser.add_argument("--aws-profile", help="Optional AWS profile name; never credential material")
    parser.add_argument("--output", help="Optional JSON output path for the discovery snapshot")
    args = parser.parse_args()

    if args.aws_profile:
        lowered = args.aws_profile.lower()
        if any(token in lowered for token in ("secret", "access_key", "aws_secret", "sk-")):
            raise SystemExit("--aws-profile must be a profile name, not credential material")
        os.environ["AWS_PROFILE"] = args.aws_profile

    import boto3  # type: ignore[import-not-found]

    session = boto3.Session(profile_name=args.aws_profile, region_name=args.region)
    client = session.client("braket", region_name=args.region)
    candidates = discover_online_qpus(client, region=args.region)
    payload = candidates_as_dict(candidates)

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not candidates:
        print(f"No ONLINE QPUs returned for region {args.region} under the active AWS profile.")
        return 0

    for index, row in enumerate(candidates, 1):
        queues = ", ".join(
            f"{item.get('queue','?')}={item.get('queueSize','?')}({item.get('queuePriority','')})"
            for item in row.queue_info
        ) or "not_recorded"
        print(f"[{index}] provider={row.provider_name} name={row.device_name} region={row.region}")
        print(f"    arn={row.device_arn}")
        print(f"    status={row.device_status} queues={queues}")
        print(f"    capabilities_digest={row.device_capabilities_digest}")
        print(f"    snapshot_digest={row.device_snapshot_digest}")

    print("claim_control=device discovery is read-only metadata, not QPU execution or readiness evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

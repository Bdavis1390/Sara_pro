#!/usr/bin/env python3
"""Scan repository text for cryptographic migration surfaces."""

from __future__ import annotations

import argparse

from worldshepherd_sara.pqc_inventory import scan_repository, write_inventory


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=".qrf-artifacts/pqc_inventory_scan.json")
    parser.add_argument(
        "--fail-on-private-key",
        action="store_true",
        help="Return non-zero when private key material is detected.",
    )
    args = parser.parse_args()

    report = scan_repository(args.root)
    out = write_inventory(report, args.output)
    print(f"{out}: {report['finding_count']} findings across {report['files_scanned']} files")
    if args.fail_on_private_key and int(report["critical_count"]) > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

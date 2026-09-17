#!/usr/bin/env python3
"""Check the current OCSF semantic anchors required by the trust-base conformance pilot.

This is intentionally narrow. It verifies that an OCSF schema checkout still
contains the existing anchors this pilot relies on; it does not assert that the
proposed class in ocsf/ocsf-schema#1724 has been accepted.
"""

import argparse
import json
from pathlib import Path

REQUIRED = {
    "objects/ai_agent.json": (
        {"name": "ai_agent"},
        ["uid", "instance_uid", "version", "charter", "ai_model"],
    ),
    "profiles/record_integrity.json": (
        {"name": "record_integrity"},
        ["attestation_list"],
    ),
    "objects/attestation.json": (
        {"name": "attestation"},
        ["authority_uid", "chain_uid", "fingerprint", "prev_event", "signatures"],
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that an OCSF schema checkout still exposes the semantic "
            "anchors required by the Worldshepherd trust-base pilot."
        )
    )
    parser.add_argument("ocsf_schema_root", help="Path to an ocsf/ocsf-schema checkout")
    args = parser.parse_args()
    root = Path(args.ocsf_schema_root)

    failures = []
    for rel, (top_level, required_attrs) in REQUIRED.items():
        path = root / rel
        if not path.is_file():
            failures.append(f"missing {rel}")
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append(f"invalid JSON {rel}: {exc}")
            continue

        for key, expected in top_level.items():
            actual = data.get(key)
            if actual != expected:
                failures.append(
                    f"{rel}: expected {key}={expected!r}, got {actual!r}"
                )

        attrs = data.get("attributes", {})
        for attr in required_attrs:
            if attr not in attrs:
                failures.append(f"{rel}: missing attribute {attr}")

    if failures:
        print("OCSF anchor check: FAIL")
        for item in failures:
            print(f"- {item}")
        return 1

    print("OCSF anchor check: PASS")
    print("- ai_agent identity/configuration anchors present")
    print("- record_integrity attestation_list present")
    print("- attestation chain/fingerprint/signature anchors present")
    print("Note: this confirms current anchors only, not acceptance of issue #1724.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_internal_readiness import audit_internal_closure


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate internally controllable QRF closure audit")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = audit_internal_closure(args.root)
    if not payload["meets_target"]:
        raise SystemExit(f"internal QRF closure below target: {payload['score']} < {payload['target']}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

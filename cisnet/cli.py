from __future__ import annotations

import argparse
import json

from .simulator import build_reference_simulation


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Worldshepherd CISNET-DEMO-01")
    parser.add_argument("--payload-gb", type=float, default=100.0, help="decimal GB payload size (default: 100)")
    parser.add_argument("--max-time", type=int, default=5000, help="simulation timeout in seconds")
    args = parser.parse_args()
    if args.payload_gb <= 0:
        parser.error("--payload-gb must be positive")
    payload_bytes = int(args.payload_gb * 1_000_000_000)
    sim = build_reference_simulation(payload_bytes=payload_bytes)
    result = sim.run(max_time_s=args.max_time)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.completed and result.ledger_valid and result.dropped_bytes == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

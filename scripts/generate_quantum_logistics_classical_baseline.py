#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_logistics_ortools import solve_family_file


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="benchmarks/quantum/logistics_cp_sat_fixture.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--time-limit-seconds", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=9675)
    args = parser.parse_args()

    result = solve_family_file(
        args.input,
        time_limit_seconds_per_instance=args.time_limit_seconds,
        random_seed=args.seed,
    )
    payload = result.to_dict()
    payload["schema_version"] = "1.0"
    payload["evidence_class"] = "controlled_strong_classical_comparator_capability"
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result.all_instances_optimal:
        return 2
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the WS-QBENCH-MGRAPH v0.1 bounded reproducibility sweep."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .magnetic_graph import sweep_eta
except ImportError:
    from magnetic_graph import sweep_eta


DEFAULT_ETAS = [0.01, 0.05, 0.10, 0.20, 0.50, 1.00, 1.50, 2.00]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nmax", type=int, default=48)
    parser.add_argument("--loop-samples", type=int, default=1000)
    parser.add_argument("--edge-threshold", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=9675)
    parser.add_argument("--etas", type=float, nargs="*", default=DEFAULT_ETAS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = sweep_eta(
        args.etas,
        nmax=args.nmax,
        loop_samples=args.loop_samples,
        rel_edge_threshold=args.edge_threshold,
        seed=args.seed,
    )
    payload = {
        "schema": "ws-qbench-mgraph/v0.1",
        "claim_state": [
            "IMPLEMENTED IN SOFTWARE",
            "SIMULATED ONLY",
            "SUPPORTED BY LITERATURE",
            "REQUIRES INDEPENDENT NUMERICAL REPRODUCTION",
        ],
        "parameters": {
            "nmax": args.nmax,
            "loop_samples": args.loop_samples,
            "edge_threshold": args.edge_threshold,
            "seed": args.seed,
            "etas": args.etas,
        },
        "results": [row.to_dict() for row in rows],
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

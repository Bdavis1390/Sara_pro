#!/usr/bin/env python3
"""Generate governed simulation evidence for QRF-BELL-001."""

from __future__ import annotations

import argparse

from worldshepherd_sara.quantum_evidence import build_bell_evidence_bundle, write_evidence_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--qasm",
        default="benchmarks/quantum/bell_qasm3.qasm",
        help="Path to the governed OpenQASM 3 program.",
    )
    parser.add_argument(
        "--output",
        default=".qrf-artifacts/qrf_bell_001_simulation_evidence.json",
        help="Output JSON path.",
    )
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=9675)
    args = parser.parse_args()

    bundle = build_bell_evidence_bundle(args.qasm, shots=args.shots, seed=args.seed)
    out = write_evidence_bundle(bundle, args.output)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

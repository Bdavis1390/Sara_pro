#!/usr/bin/env python3
"""Run QRF-BELL-001 through an explicitly selected CUDA-Q target."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_cudaq import run_bell_cudaq


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen QRF Bell benchmark through CUDA-Q")
    parser.add_argument("--target", default="qpp-cpu")
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument(
        "--target-options-json",
        default="{}",
        help="JSON object passed to cudaq.set_target; do not put secrets on the command line or in this JSON",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    options = json.loads(args.target_options_json)
    if not isinstance(options, dict):
        raise SystemExit("--target-options-json must decode to an object")
    forbidden = {key for key in options if any(token in key.lower() for token in ("token", "password", "secret", "api_key", "apikey"))}
    if forbidden:
        raise SystemExit(
            "Do not pass credentials in --target-options-json; use the provider's documented environment/config mechanism. "
            f"Forbidden-looking fields: {sorted(forbidden)}"
        )

    result = run_bell_cudaq(target=args.target, shots=args.shots, target_options=options)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(
        f"{output}: requested_target={result.requested_target} resolved_target={result.resolved_target} "
        f"evidence_class={result.evidence_class}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

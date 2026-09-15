from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from worldshepherd_sara.quantum_optimization import (
    logistics_surrogate_problem,
    metasurface_surrogate_problem,
    run_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate governed QRF application benchmark evidence")
    parser.add_argument("--output", required=True)
    parser.add_argument("--grid-size", type=int, default=17)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=9675)
    args = parser.parse_args()

    results = [
        run_benchmark(
            metasurface_surrogate_problem(),
            benchmark_id="WS-META-QO-001",
            instance_kind="synthetic_reduced_order_surrogate",
            grid_size=args.grid_size,
            shots=args.shots,
            seed=args.seed,
        ),
        run_benchmark(
            logistics_surrogate_problem(),
            benchmark_id="WS-LOG-QO-001",
            instance_kind="synthetic_assignment_surrogate",
            grid_size=args.grid_size,
            shots=args.shots,
            seed=args.seed,
        ),
    ]

    payload = {
        "schema_version": "1.0",
        "evidence_level": "ideal_and_noisy_simulation",
        "benchmark_count": len(results),
        "claim_control": (
            "Synthetic application surrogates validate the QRF benchmark pipeline only. "
            "They are not calibrated EM or mission models and do not establish quantum advantage."
        ),
        "results": [asdict(result) for result in results],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

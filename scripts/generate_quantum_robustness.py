from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_optimization import logistics_surrogate_problem, metasurface_surrogate_problem
from worldshepherd_sara.quantum_robustness import sweep_problem


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate QRF quantum optimization robustness evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = {
        "schema_version": "1.0",
        "results": [
            sweep_problem(
                metasurface_surrogate_problem(),
                benchmark_id="WS-META-QO-001",
                instance_kind="synthetic_reduced_order_surrogate",
            ),
            sweep_problem(
                logistics_surrogate_problem(),
                benchmark_id="WS-LOG-QO-001",
                instance_kind="synthetic_assignment_surrogate",
            ),
        ],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

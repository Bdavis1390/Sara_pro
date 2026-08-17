from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_microsoft_resource import estimate_file_sensitivity


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate governed Microsoft QDK resource sensitivity evidence")
    parser.add_argument("--input", default="benchmarks/quantum/qrf_resource_smoke.qasm")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = estimate_file_sensitivity(
        Path(args.input),
        benchmark_id="QRF-RESOURCE-SENS-001",
        logical_qubits=2,
        logical_gate_count=3,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

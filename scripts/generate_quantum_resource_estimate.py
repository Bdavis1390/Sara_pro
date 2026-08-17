from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_microsoft_resource import estimate_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Microsoft QDK resource-estimator evidence")
    parser.add_argument("--program", default="benchmarks/quantum/bell_qasm3.qasm")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = estimate_file(
        args.program,
        benchmark_id="QRF-BELL-001",
        logical_qubits=2,
        logical_gate_count=2,
        max_error=0.01,
        physical_error_rate=1e-4,
        gate_time_ns=100.0,
        measurement_time_ns=500.0,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

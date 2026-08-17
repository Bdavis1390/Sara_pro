#!/usr/bin/env python3
"""Execute QRF-BELL-001 on IBM quantum hardware when credentials are injected."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_ibm import run_bell_on_ibm_hardware


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=os.getenv("IBM_QUANTUM_BACKEND"))
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument(
        "--output",
        default=".qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json",
    )
    args = parser.parse_args()

    token = os.getenv("IBM_QUANTUM_TOKEN", "")
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    result = run_bell_on_ibm_hardware(
        token=token,
        instance=instance,
        backend_name=args.backend,
        shots=args.shots,
        optimization_level=args.optimization_level,
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{out}: backend={result.backend} job_id={result.job_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

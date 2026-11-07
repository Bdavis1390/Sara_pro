"""WS-QBENCH-MGRAPH Kaggle replay harness v0.11.

Runs the bounded source-locked numerical controls in a CPU-only Kaggle environment,
records source-file SHA-256 values and test outputs, and preserves all claim limits.
No hardware or exact-paper reproduction claim is created by a passing replay.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

CORE = (
    "README.md",
    "magnetic_graph.py",
    "validation_v02.py",
    "phase_null_v03.py",
    "localization_ablation_v04.py",
    "code_s1_ingest_v10.py",
    "requirements.txt",
)

TEST_MODULES = (
    "research.ws_qbench_mgraph_v01.tests.test_magnetic_graph",
    "research.ws_qbench_mgraph_v01.tests.test_validation_v02",
    "research.ws_qbench_mgraph_v01.tests.test_phase_null_v03",
    "research.ws_qbench_mgraph_v01.tests.test_localization_ablation_v04",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", default="qbench-kaggle-replay-v11.json")
    parser.add_argument("--benchmark-nmax", type=int, default=48)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    pkg = Path(__file__).resolve().parent

    missing = [name for name in CORE if not (pkg / name).is_file()]
    if missing:
        raise SystemExit("missing QBench source files: " + ", ".join(missing))

    source_files = {
        name: sha256_file(pkg / name)
        for name in CORE
    }

    try:
        numpy_version = importlib.metadata.version("numpy")
    except importlib.metadata.PackageNotFoundError:
        numpy_version = None

    receipt: dict[str, object] = {
        "schema": "worldshepherd.ws-qbench-mgraph.kaggle-replay.v0.11",
        "classification": "SIMULATED_NUMERICAL_INTERNAL",
        "source_sha": args.source_sha,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy_version": numpy_version,
        "source_sha256": source_files,
        "tests": [],
        "benchmark": None,
        "claims_boundary": [
            "SIMULATED_ONLY",
            "NO_HARDWARE_VALIDATION",
            "NO_EXACT_FIGURE_4EF_REPRODUCTION_CLAIM",
            "NO_EXACT_SUPPLEMENTARY_S1_REPRODUCTION_CLAIM",
            "NEGATIVE_EVIDENCE_MUST_BE_RETAINED",
        ],
    }

    overall_rc = 0
    for module in TEST_MODULES:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", module],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        receipt["tests"].append(
            {
                "module": module,
                "returncode": proc.returncode,
                "output": proc.stdout[-12000:],
            }
        )
        if proc.returncode != 0:
            overall_rc = 1

    bench = subprocess.run(
        [
            sys.executable,
            "-m",
            "research.ws_qbench_mgraph_v01.benchmark",
            "--nmax",
            str(args.benchmark_nmax),
        ],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    receipt["benchmark"] = {
        "nmax": args.benchmark_nmax,
        "returncode": bench.returncode,
        "output": bench.stdout[-12000:],
    }
    if bench.returncode != 0:
        overall_rc = 1

    out = Path(args.output)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return overall_rc


if __name__ == "__main__":
    raise SystemExit(main())

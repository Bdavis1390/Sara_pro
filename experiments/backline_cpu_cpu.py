#!/usr/bin/env python3
"""Worldshepherd QBL-G1 local CPU-to-CPU Backline validation.

Claims boundary:
- This is a simulator-backed laboratory check.
- It does not establish physical-QPU performance, RDMA performance,
  quantum advantage, or sub-microsecond/microsecond transport latency.

Upstream API pattern:
https://www.pennylane.ai/demos/backline
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np
import pennylane as qp


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def decoder_library_path() -> Path:
    root = Path(os.environ.get("CATALYST_ROOT", "~/catalyst")).expanduser()
    return root / "runtime" / "build" / "lib" / "libsteane_coprocessor_cpu.so"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def environment_manifest(decoder_path: Path) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "pennylane": getattr(qp, "__version__", None),
        "pennylane_catalyst_distribution": _distribution_version("pennylane-catalyst"),
        "pennylane_lightning_distribution": _distribution_version("pennylane-lightning"),
        "decoder_library": str(decoder_path),
        "decoder_library_exists": decoder_path.is_file(),
        "decoder_library_sha256": sha256_file(decoder_path) if decoder_path.is_file() else None,
        "transport": "memcpy",
        "qec_code": "steane",
        "quantum_device": "lightning.qubit",
        "claims_state": "REQUIRES_LAB_VALIDATION",
    }


def build_ghz_qnode(shots: int = 10):
    decoder_path = decoder_library_path()
    if not decoder_path.is_file():
        raise FileNotFoundError(
            f"Steane coprocessor library not found: {decoder_path}. "
            "Set CATALYST_ROOT to the pinned Catalyst environment."
        )

    steane_decode = qp.CoprocessorFunction("steane_coprocessor", str(decoder_path))
    quantum_device = qp.device("lightning.qubit", wires=3)

    controller = qp.Controller(device=quantum_device)
    coprocessor = qp.Coprocessor(coprocessor_fn=steane_decode)
    backline = qp.Backline(
        controller=controller,
        coprocessors=[coprocessor],
        transport="memcpy",
        qec_code="steane",
    )

    @qp.qjit(capture=True)
    @qp.set_shots(shots)
    @qp.qnode(backline, mcm_method="one-shot")
    def ghz():
        qp.Hadamard(0)
        qp.CNOT([0, 1])
        qp.CNOT([1, 2])
        return qp.sample([qp.measure(0), qp.measure(1), qp.measure(2)])

    return ghz


def ghz_samples_valid(samples: Any) -> bool:
    values = np.asarray(samples)
    if values.ndim != 2 or values.shape[1] != 3:
        return False

    binary = np.logical_or(values == 0, values == 1)
    all_equal = np.all(values == values[:, :1], axis=1)
    return bool(np.all(binary) and np.all(all_equal))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.shots < 1 or args.repeat < 1:
        parser.error("--shots and --repeat must be positive integers")

    decoder_path = decoder_library_path()
    manifest = environment_manifest(decoder_path)

    try:
        ghz = build_ghz_qnode(shots=args.shots)
        results = []
        failures = 0

        for index in range(args.repeat):
            samples = ghz()
            valid = ghz_samples_valid(samples)
            failures += 0 if valid else 1
            results.append(
                {
                    "iteration": index + 1,
                    "valid_ghz_samples": valid,
                    "samples": np.asarray(samples).tolist(),
                }
            )

        report = {
            "gate": "QBL-G1",
            "status": "PASS" if failures == 0 else "FAIL",
            "manifest": manifest,
            "repeat": args.repeat,
            "shots": args.shots,
            "ghz_validation_failures": failures,
            "results": results,
            "claims_boundary": {
                "worldshepherd_backline_integration": (
                    "PROVEN_INTERNALLY_QBL_G1_SCOPE_ONLY"
                    if failures == 0
                    else "REQUIRES_LAB_VALIDATION"
                ),
                "sub_3us_performance": "NOT_CURRENTLY_CLAIMED",
                "hardware_qpu_integration": "NOT_CURRENTLY_CLAIMED",
                "quantum_advantage": "NOT_CURRENTLY_CLAIMED",
            },
        }
    except Exception as exc:  # Preserve setup/runtime failures as evidence.
        report = {
            "gate": "QBL-G1",
            "status": "ERROR",
            "manifest": manifest,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "claims_boundary": {
                "worldshepherd_backline_integration": "REQUIRES_LAB_VALIDATION"
            },
        }

    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"QBL-G1 status: {report['status']}")
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

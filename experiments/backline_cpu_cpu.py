#!/usr/bin/env python3
"""Worldshepherd QBL-G1 local CPU-to-CPU Backline validation.

QBL-G1A reproduces the upstream Tier-1/Demo-1 device choice (``null.qubit``).
QBL-G1B exercises the Worldshepherd compatibility extension (``lightning.qubit``).

Claims boundary:
- These are simulator-backed laboratory checks.
- They do not establish physical-QPU performance, RDMA performance,
  quantum advantage, or sub-3-microsecond Worldshepherd performance.
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


def decoder_library_candidates() -> list[Path]:
    candidates: list[Path] = []

    explicit = os.environ.get("BACKLINE_STEANE_DECODER")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    catalyst_root = os.environ.get("CATALYST_ROOT")
    if catalyst_root:
        candidates.append(
            Path(catalyst_root).expanduser()
            / "runtime"
            / "build"
            / "lib"
            / "libsteane_coprocessor_cpu.so"
        )

    try:
        from catalyst.utils.runtime_environment import get_lib_path

        candidates.append(
            Path(get_lib_path("runtime", "RUNTIME_LIB_DIR"))
            / "libsteane_coprocessor_cpu.so"
        )
    except Exception:
        # Preserve candidate discovery as a non-fatal setup concern; the caller
        # reports a precise missing-library error if no candidate exists.
        pass

    default_source = (
        Path("~/catalyst").expanduser()
        / "runtime"
        / "build"
        / "lib"
        / "libsteane_coprocessor_cpu.so"
    )
    candidates.append(default_source)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def decoder_library_path() -> Path:
    candidates = decoder_library_candidates()
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if candidates:
        return candidates[0]
    return Path("libsteane_coprocessor_cpu.so")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gate_for_device(device_name: str) -> str:
    if device_name == "null.qubit":
        return "QBL-G1A"
    if device_name == "lightning.qubit":
        return "QBL-G1B"
    raise ValueError(f"unsupported QBL-G1 device: {device_name}")


def environment_manifest(decoder_path: Path, device_name: str) -> dict[str, Any]:
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
        "decoder_search_candidates": [str(path) for path in decoder_library_candidates()],
        "transport": "memcpy",
        "qec_code": "steane",
        "quantum_device": device_name,
        "claims_state": "REQUIRES_LAB_VALIDATION",
    }


def build_ghz_qnode(shots: int = 10, device_name: str = "lightning.qubit"):
    gate_for_device(device_name)
    decoder_path = decoder_library_path()
    if not decoder_path.is_file():
        searched = ", ".join(str(path) for path in decoder_library_candidates())
        raise FileNotFoundError(
            "Steane coprocessor library not found. "
            f"Searched: {searched}. Set BACKLINE_STEANE_DECODER explicitly if needed."
        )

    steane_decode = qp.CoprocessorFunction(
        "steane_coprocessor", lib_path=str(decoder_path)
    )
    quantum_device = qp.device(device_name, wires=3)

    controller = qp.Controller(name="cpu-controller", device=quantum_device)
    coprocessor = qp.Coprocessor(name="cpu-coproc", coprocessor_fn=steane_decode)
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
    parser.add_argument(
        "--device",
        choices=("null.qubit", "lightning.qubit"),
        default="lightning.qubit",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    if args.shots < 1 or args.repeat < 1:
        parser.error("--shots and --repeat must be positive integers")

    gate = gate_for_device(args.device)
    decoder_path = decoder_library_path()
    manifest = environment_manifest(decoder_path, args.device)

    try:
        ghz = build_ghz_qnode(shots=args.shots, device_name=args.device)
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

        scope_claim = f"PROVEN_INTERNALLY_{gate}_SCOPE_ONLY"
        report = {
            "gate": gate,
            "status": "PASS" if failures == 0 else "FAIL",
            "manifest": manifest,
            "repeat": args.repeat,
            "shots": args.shots,
            "ghz_validation_failures": failures,
            "results": results,
            "claims_boundary": {
                "worldshepherd_backline_integration": (
                    scope_claim if failures == 0 else "REQUIRES_LAB_VALIDATION"
                ),
                "sub_3us_performance": "NOT_CURRENTLY_CLAIMED",
                "hardware_qpu_integration": "NOT_CURRENTLY_CLAIMED",
                "quantum_advantage": "NOT_CURRENTLY_CLAIMED",
            },
        }
    except Exception as exc:  # Preserve setup/runtime failures as evidence.
        report = {
            "gate": gate,
            "status": "ERROR",
            "manifest": manifest,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "claims_boundary": {
                "worldshepherd_backline_integration": "REQUIRES_LAB_VALIDATION",
                "sub_3us_performance": "NOT_CURRENTLY_CLAIMED",
                "hardware_qpu_integration": "NOT_CURRENTLY_CLAIMED",
                "quantum_advantage": "NOT_CURRENTLY_CLAIMED",
            },
        }

    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{gate} status: {report['status']}")
        print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""BAROS Kaggle synthetic replay gate.

NON-CLINICAL. NOT FOR PATIENT CARE OR TREATMENT PLANNING.

This runner refuses to execute the BAROS synthetic verification suite unless the
Kaggle Python environment matches the repository's exact pinned dependency versions.
It emits a machine-readable receipt and never upgrades clinical/scientific claims.
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

EXPECTED_PYTHON = "3.12.15"

EXPECTED = {
    "numpy": "2.5.3",
    "numba": "0.67.0",
    "pydicom": "3.0.2",
    "pymedphys": "0.41.0",
    "pytest": "9.1.1",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in EXPECTED:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", default="baros-kaggle-replay-receipt.json")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    req = root / "baros" / "requirements.txt"
    tests = sorted((root / "tests").glob("test_baros_*.py"))
    if not req.is_file() or not tests:
        raise SystemExit("BAROS source/test layout incomplete")

    observed_python = platform.python_version()
    observed = versions()
    mismatches = {
        name: {"expected": expected, "observed": observed.get(name)}
        for name, expected in EXPECTED.items()
        if observed.get(name) != expected
    }

    receipt: dict[str, object] = {
        "schema": "worldshepherd.baros.kaggle-synthetic-replay.v1",
        "classification": "NON_CLINICAL_SYNTHETIC_INTERNAL",
        "source_sha": args.source_sha,
        "python": sys.version,
        "platform": platform.platform(),
        "requirements_sha256": sha256_file(req),
        "expected_python": EXPECTED_PYTHON,
        "observed_python": observed_python,
        "expected_dependencies": EXPECTED,
        "observed_dependencies": observed,
        "environment_match": (observed_python == EXPECTED_PYTHON and not mismatches),
        "dependency_mismatches": mismatches,
        "test_files": [str(p.relative_to(root)) for p in tests],
        "test_execution_performed": False,
        "pytest_returncode": None,
        "claims_boundary": [
            "NON_CLINICAL",
            "NOT_FOR_PATIENT_CARE",
            "SYNTHETIC_INTERNAL_ONLY",
            "DEPENDENCY_MATCH_REQUIRED_BEFORE_TEST_EXECUTION",
            "NO_CLINICAL_VALIDATION_CLAIM",
        ],
    }

    rc = 3
    if observed_python != EXPECTED_PYTHON:
        receipt["python_mismatch"] = {
            "expected": EXPECTED_PYTHON,
            "observed": observed_python,
        }
    if observed_python == EXPECTED_PYTHON and not mismatches:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *map(str, tests)],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        receipt["test_execution_performed"] = True
        receipt["pytest_returncode"] = proc.returncode
        receipt["pytest_output"] = proc.stdout[-20000:]
        rc = 0 if proc.returncode == 0 else 1

    out = Path(args.output)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

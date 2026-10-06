from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent
DEFAULT_BACKEND = ROOT / "manifests" / "backend_selection_b000.json"
DEFAULT_CONVERGENCE = ROOT / "manifests" / "convergence_b000.json"


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _process_cmdlines() -> list[str]:
    out = []
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace").strip()
        except (OSError, PermissionError):
            continue
        if raw:
            out.append(raw)
    return out


def _memory_snapshot() -> dict[str, float]:
    values: dict[str, float] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            fields = rest.split()
            if not fields:
                continue
            # /proc/meminfo reports these values in kB.
            values[key] = float(fields[0]) / (1024 ** 2)
    except (OSError, ValueError):
        return {"MemAvailable_GB": 0.0, "SwapFree_GB": 0.0}
    return {
        "MemAvailable_GB": values.get("MemAvailable", 0.0),
        "SwapFree_GB": values.get("SwapFree", 0.0),
    }


def _runtime_env(runtime_root: Path | None) -> dict[str, str]:
    env = os.environ.copy()
    if runtime_root is None:
        return env

    libdirs = [
        runtime_root / "usr/lib/x86_64-linux-gnu",
        runtime_root / "lib/x86_64-linux-gnu",
    ]
    staged = ":".join(str(p) for p in libdirs if p.exists())
    existing = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = staged + ((":" + existing) if staged and existing else existing)
    env["OPAL_PREFIX"] = str(runtime_root / "usr")
    env["PATH"] = str(runtime_root / "usr/bin") + os.pathsep + env.get("PATH", "")
    return env


def _missing_libraries(binary: Path, runtime_root: Path | None = None) -> list[str]:
    try:
        result = subprocess.run(
            ["ldd", str(binary)],
            check=False,
            text=True,
            capture_output=True,
            timeout=10,
            env=_runtime_env(runtime_root),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ["ldd_check_failed"]
    missing = []
    for line in result.stdout.splitlines():
        if "=> not found" in line:
            missing.append(line.split("=>", 1)[0].strip())
    return sorted(set(missing))


def inspect_host(
    *,
    work_root: Path,
    backend_binary: Path,
    expected_backend_sha256: str,
    blocked_process_terms: list[str],
    minimum_free_gb: float,
    minimum_mem_available_gb: float = 0.0,
    minimum_swap_free_gb: float = 0.0,
    runtime_root: Path | None = None,
    startup_sanity_passed: bool = False,
) -> dict:
    cmdlines = _process_cmdlines()
    blockers = sorted(
        {
            term
            for term in blocked_process_terms
            if any(term in cmd for cmd in cmdlines)
        }
    )
    palace_clear = not blockers

    usage = shutil.disk_usage(work_root if work_root.exists() else work_root.parent)
    free_gb = usage.free / (1024 ** 3)
    storage_clear = free_gb >= minimum_free_gb

    memory = _memory_snapshot()
    memory_clear = memory["MemAvailable_GB"] >= minimum_mem_available_gb
    swap_clear = memory["SwapFree_GB"] >= minimum_swap_free_gb

    backend_exists = backend_binary.exists()
    backend_sha = _sha256(backend_binary) if backend_exists else None
    backend_hash_clear = backend_exists and backend_sha == expected_backend_sha256
    missing = (
        _missing_libraries(backend_binary, runtime_root)
        if backend_exists
        else ["backend_missing"]
    )
    runtime_clear = backend_exists and not missing

    clear = (
        palace_clear
        and storage_clear
        and memory_clear
        and swap_clear
        and backend_hash_clear
        and runtime_clear
        and startup_sanity_passed
    )
    return {
        "palace_clear": palace_clear,
        "process_blockers": blockers,
        "work_root": str(work_root),
        "work_root_free_GB": free_gb,
        "storage_clear": storage_clear,
        "MemAvailable_GB": memory["MemAvailable_GB"],
        "minimum_mem_available_GB": minimum_mem_available_gb,
        "memory_clear": memory_clear,
        "SwapFree_GB": memory["SwapFree_GB"],
        "minimum_swap_free_GB": minimum_swap_free_gb,
        "swap_clear": swap_clear,
        "backend_binary": str(backend_binary),
        "backend_exists": backend_exists,
        "backend_sha256_actual": backend_sha,
        "backend_hash_clear": backend_hash_clear,
        "runtime_root": None if runtime_root is None else str(runtime_root),
        "missing_runtime_libraries": missing,
        "runtime_clear": runtime_clear,
        "startup_sanity_passed": startup_sanity_passed,
        "execution_clear": clear,
        "decision": "ALLOW_FIRST_CONVERGENCE_CASE" if clear else "BLOCK_DFT_EXECUTION",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, default=Path("/var/tmp/ws-altermag-runs"))
    parser.add_argument(
        "--backend-binary",
        type=Path,
        default=Path("/var/tmp/ws-altermag-elk-cache/pkg/usr/bin/elk-lapw"),
    )
    parser.add_argument(
        "--runtime-root",
        type=Path,
        default=Path("/var/tmp/ws-altermag-elk-cache/runtime"),
    )
    args = parser.parse_args()

    backend = json.loads(DEFAULT_BACKEND.read_text(encoding="utf-8"))
    conv = json.loads(DEFAULT_CONVERGENCE.read_text(encoding="utf-8"))
    elk = backend["selection"]["open_crosscheck"]
    expected = elk["extracted_binary_sha256"]
    startup_passed = elk.get("staged_startup_sanity", {}).get("status") == "PASS_EXPECTED_NO_INPUT_STOP"
    gate = conv["resource_gate"]

    result = inspect_host(
        work_root=args.work_root,
        backend_binary=args.backend_binary,
        expected_backend_sha256=expected,
        blocked_process_terms=list(gate["block_if_process_contains"]),
        minimum_free_gb=float(gate["minimum_work_root_free_GB"]),
        minimum_mem_available_gb=float(gate["minimum_mem_available_GB"]),
        minimum_swap_free_gb=float(gate["minimum_swap_free_GB"]),
        runtime_root=args.runtime_root,
        startup_sanity_passed=startup_passed,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

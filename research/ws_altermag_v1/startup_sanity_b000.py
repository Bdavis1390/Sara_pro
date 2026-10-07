from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def evaluate_transcript(stdout: str, info_out_exists: bool, version: str = "7.2.42") -> dict:
    started = f"Elk code version {version} started" in stdout
    no_input_stop = "Error(readinput): error opening elk.in" in stdout
    passed = started and no_input_stop and not info_out_exists
    return {
        "version_started": started,
        "expected_no_input_stop": no_input_stop,
        "info_out_created": info_out_exists,
        "pass": passed,
    }


def run_startup_sanity(
    *,
    backend_binary: Path,
    runtime_root: Path,
    expected_binary_sha256: str,
    timeout_seconds: float = 5.0,
) -> dict:
    actual_hash = _sha256(backend_binary)
    if actual_hash != expected_binary_sha256:
        return {
            "pass": False,
            "decision": "BLOCK_HASH_MISMATCH",
            "backend_sha256_actual": actual_hash,
        }

    env = os.environ.copy()
    libdirs = [
        runtime_root / "usr/lib/x86_64-linux-gnu",
        runtime_root / "lib/x86_64-linux-gnu",
    ]
    env["LD_LIBRARY_PATH"] = ":".join(str(p) for p in libdirs if p.exists())
    env["OPAL_PREFIX"] = str(runtime_root / "usr")
    env["PATH"] = str(runtime_root / "usr/bin") + os.pathsep + env.get("PATH", "")

    with tempfile.TemporaryDirectory(prefix="ws-altermag-startup-") as td:
        workdir = Path(td)
        assert not (workdir / "elk.in").exists()
        try:
            proc = subprocess.run(
                [str(backend_binary)],
                cwd=workdir,
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            proc = None
            timed_out = True
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
        else:
            stdout = proc.stdout
            stderr = proc.stderr

        info_exists = (workdir / "INFO.OUT").exists()
        transcript = evaluate_transcript(stdout, info_exists)
        passed = transcript["pass"] and not timed_out

        return {
            "pass": passed,
            "decision": "STARTUP_SANITY_PASS" if passed else "STARTUP_SANITY_FAIL",
            "timed_out": timed_out,
            "return_code": None if proc is None else proc.returncode,
            "backend_sha256_actual": actual_hash,
            "stdout": stdout,
            "stderr": stderr,
            "transcript": transcript,
            "claim_boundary": (
                "This startup sanity test deliberately provides no elk.in. Passing proves only that the "
                "content-pinned binary and staged runtime reach Elk input parsing; it performs no SCF/DFT calculation."
            ),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-binary", required=True, type=Path)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_startup_sanity(
        backend_binary=args.backend_binary,
        runtime_root=args.runtime_root,
        expected_binary_sha256=args.expected_sha256,
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

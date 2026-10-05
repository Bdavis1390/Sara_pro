from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

from .convergence_b000 import DEFAULT_PLAN
from .elk_input_b000 import render_elk_template
from .execution_gate import DEFAULT_BACKEND, inspect_host


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _runtime_env(runtime_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    libdirs = [
        runtime_root / "usr/lib/x86_64-linux-gnu",
        runtime_root / "lib/x86_64-linux-gnu",
    ]
    env["LD_LIBRARY_PATH"] = ":".join(str(p) for p in libdirs if p.exists())
    env["OPAL_PREFIX"] = str(runtime_root / "usr")
    env["PATH"] = str(runtime_root / "usr/bin") + os.pathsep + env.get("PATH", "")
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    return env


def _first_case(plan: dict) -> dict:
    return {
        "label": "basis-rgkmax-6.0",
        "kgrid": list(plan["basis_convergence"]["fixed_kgrid"]),
        "rgkmax": float(plan["basis_convergence"]["rgkmax_values"][0]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, default=Path("/var/tmp/ws-altermag-runs"))
    parser.add_argument("--backend-root", type=Path, default=Path("/var/tmp/ws-altermag-elk-cache"))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=14400)
    args = parser.parse_args()

    backend_manifest = json.loads(DEFAULT_BACKEND.read_text(encoding="utf-8"))
    plan = json.loads(DEFAULT_PLAN.read_text(encoding="utf-8"))
    elk = backend_manifest["selection"]["open_crosscheck"]

    backend_binary = args.backend_root / "pkg/usr/bin/elk-lapw"
    runtime_root = args.backend_root / "runtime"
    species_path = args.backend_root / "pkg/usr/share/elk-lapw/species"
    startup_ok = elk.get("staged_startup_sanity", {}).get("status") == "PASS_EXPECTED_NO_INPUT_STOP"

    gate = inspect_host(
        work_root=args.work_root,
        backend_binary=backend_binary,
        expected_backend_sha256=elk["extracted_binary_sha256"],
        blocked_process_terms=list(plan["resource_gate"]["block_if_process_contains"]),
        minimum_free_gb=float(plan["resource_gate"]["minimum_work_root_free_GB"]),
        runtime_root=runtime_root,
        startup_sanity_passed=startup_ok,
    )

    case = _first_case(plan)
    proposal = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-FIRST-CASE",
        "case": case,
        "gate": gate,
        "execute_requested": bool(args.execute),
        "claim_boundary": "A prepared or completed first convergence case is not a converged CrSb physics result.",
    }

    if not gate["execution_clear"]:
        proposal["decision"] = "BLOCK_DFT_EXECUTION"
        print(json.dumps(proposal, indent=2, sort_keys=True))
        raise SystemExit(3)

    if not args.execute:
        proposal["decision"] = "READY_BUT_NOT_EXECUTED"
        print(json.dumps(proposal, indent=2, sort_keys=True))
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.work_root / f"{stamp}-{case['label']}"
    run_dir.mkdir(parents=True, exist_ok=False)

    elk_input = render_elk_template(
        ngridk=tuple(case["kgrid"]),
        rgkmax=case["rgkmax"],
        species_path=str(species_path) + "/",
    )
    input_path = run_dir / "elk.in"
    input_path.write_text(elk_input, encoding="utf-8")

    env = _runtime_env(runtime_root)
    try:
        proc = subprocess.run(
            [str(backend_binary)],
            cwd=run_dir,
            env=env,
            text=True,
            capture_output=True,
            timeout=args.timeout_seconds,
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

    (run_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8")

    receipt = {
        **proposal,
        "decision": "FIRST_CASE_EXECUTED",
        "run_dir": str(run_dir),
        "input_sha256": _sha256(input_path),
        "timed_out": timed_out,
        "return_code": None if proc is None else proc.returncode,
        "info_out_exists": (run_dir / "INFO.OUT").exists(),
        "output_files": sorted(p.name for p in run_dir.iterdir() if p.is_file()),
        "claim_status": ["SIMULATED ONLY"],
    }
    (run_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

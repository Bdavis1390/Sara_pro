from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def receipt_rows(tsv: Path) -> dict[int, dict]:
    if not tsv.is_file():
        return {}
    with tsv.open(encoding="utf-8", newline="") as fh:
        return {
            int(row["anchor_id"]): row
            for row in csv.DictReader(fh, delimiter="\t")
        }


def audit_case(
    work_root: Path,
    anchor: int,
    receipt: dict | None,
    *,
    expected_points: int = 161,
    first_ghz: float = 9.20,
    spacing_ghz: float = 0.01,
) -> dict:
    candidates = sorted(work_root.glob(f"A{anchor:03d}-*"))
    if len(candidates) != 1:
        return {
            "anchor": anchor,
            "decision": "HOLD_MISSING_OR_AMBIGUOUS_RUN_DIRECTORY",
            "candidate_count": len(candidates),
        }
    work_dir = candidates[0]
    csv_path = work_dir / "palace-output" / "port-S.csv"
    stdout_path = work_dir / "stdout.txt"
    if not csv_path.is_file() or not stdout_path.is_file():
        return {
            "anchor": anchor,
            "work_dir": str(work_dir),
            "decision": "HOLD_MISSING_EVIDENCE",
        }

    with csv_path.open(encoding="utf-8", newline="") as fh:
        raw = list(csv.reader(fh))
    freqs = []
    bad_rows = 0
    for row in raw[1:]:
        try:
            freqs.append(float(row[0]))
        except (ValueError, IndexError):
            bad_rows += 1
    expected = {round(first_ghz + spacing_ghz * i, 6)
                for i in range(expected_points)}
    actual = [round(x, 6) for x in freqs]
    missing = sorted(expected.difference(actual))
    extra = sorted(set(actual).difference(expected))
    duplicates = len(actual) - len(set(actual))

    output = stdout_path.read_text(encoding="utf-8", errors="replace")
    warnings = output.count("GMRES solver did NOT converge")
    linear_warnings = output.count("Linear solver did not converge")
    success = (
        receipt is not None
        and receipt.get("exit_code") == "0"
        and receipt.get("status") == "EXIT0"
    )
    grid_ok = (
        not missing and not extra and not duplicates and not bad_rows
        and len(freqs) == expected_points
    )
    if warnings or linear_warnings:
        decision = "HOLD_SOLVER_NONCONVERGENCE_REVIEW"
    elif not success:
        decision = "IN_PROGRESS_OR_EXIT_NOT_RECORDED"
    elif not grid_ok:
        decision = "HOLD_INCOMPLETE_FREQUENCY_GRID"
    else:
        decision = "PROVISIONAL_SOLVER_LOG_PASS"

    return {
        "anchor": anchor,
        "work_dir": str(work_dir),
        "receipt_exit0": success,
        "observed_points": len(freqs),
        "expected_points": expected_points,
        "grid_complete": grid_ok,
        "missing_frequency_count": len(missing),
        "first_missing_frequency_ghz": missing[:5],
        "extra_frequency_count": len(extra),
        "duplicate_frequency_count": duplicates,
        "malformed_frequency_rows": bad_rows,
        "gmres_nonconvergence_count": warnings,
        "linear_solver_warning_count": linear_warnings,
        "stdout_sha256": file_sha256(stdout_path),
        "port_s_sha256": file_sha256(csv_path),
        "decision": decision,
        "claim_boundary": (
            "A completed exit-0 run with no logged GMRES warning is only a "
            "provisional solver-log pass, not a mesh convergence, error-bound "
            "or physical-validation result."
        ),
    }


def audit(root: Path, anchors: list[int]) -> dict:
    results_path = root / "execution" / "job-results.tsv"
    receipts = receipt_rows(results_path)
    return {
        "schema_version": "1.0",
        "program": "WORLDSHEPHERD-PALACE",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "results_path": str(results_path),
        "results_sha256": (
            file_sha256(results_path) if results_path.is_file() else None
        ),
        "cases": [
            audit_case(root / "work", anchor, receipts.get(anchor))
            for anchor in anchors
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--anchors", type=int, nargs="+", default=[27, 28, 29])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit(args.root, args.anchors)
    data = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(args.output)
    print(data)


if __name__ == "__main__":
    main()

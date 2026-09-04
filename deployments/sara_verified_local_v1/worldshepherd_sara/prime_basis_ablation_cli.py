from __future__ import annotations

import argparse
import json
from pathlib import Path

from .prime_basis_ablation import (
    PrimeBasisAblationReport,
    run_prime_basis_ablation,
    verify_prime_basis_ablation_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic WS-QE-2026-PRI-001 prime-basis numerical ablation."
    )
    parser.add_argument("--sample-count", type=int, default=64)
    parser.add_argument("--rank", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional UTF-8 JSON output path. Without this option the report is printed.",
    )
    parser.add_argument(
        "--verify",
        type=Path,
        help="Verify an existing JSON report and exit without running a new benchmark.",
    )
    return parser


def _serialize(report: PrimeBasisAblationReport) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.verify is not None:
        payload = json.loads(args.verify.read_text(encoding="utf-8"))
        report = PrimeBasisAblationReport.model_validate(payload)
        if not verify_prime_basis_ablation_report(report):
            print("INVALID")
            return 1
        print("VALID")
        return 0

    report = run_prime_basis_ablation(sample_count=args.sample_count, rank=args.rank)
    serialized = _serialize(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(report.report_digest)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

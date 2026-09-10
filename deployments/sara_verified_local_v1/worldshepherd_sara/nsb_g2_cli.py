from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_g2_solver import NSBG2Report, run_nsb_g2_benchmark, verify_nsb_g2_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run or verify the deterministic WS-NSB v0.7 G2 manufactured-solution benchmark."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _serialize(report: NSBG2Report) -> str:
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
        report = NSBG2Report.model_validate(payload)
        if not verify_nsb_g2_report(report):
            print("INVALID")
            return 1
        print("VALID")
        return 0

    report = run_nsb_g2_benchmark()
    serialized = _serialize(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(report.report_digest)
    else:
        print(serialized, end="")
    return 0 if report.convergence.acceptance_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

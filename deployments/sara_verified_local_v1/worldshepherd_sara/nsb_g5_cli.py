from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_g5_hartmann import NSBG5Report, run_nsb_g5_benchmark, verify_nsb_g5_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded WS-NSB v1.0 G5 quasi-static Hartmann-flow reference benchmark."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _serialize(report: NSBG5Report) -> str:
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
        report = NSBG5Report.model_validate(payload)
        if not verify_nsb_g5_report(report):
            print("INVALID")
            return 1
        if not report.acceptance.acceptance_pass:
            print("VALID-BUT-GATE-FAILED")
            return 2
        print("VALID")
        return 0

    report = run_nsb_g5_benchmark()
    serialized = _serialize(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(report.report_digest)
    else:
        print(serialized, end="")
    return 0 if report.acceptance.acceptance_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

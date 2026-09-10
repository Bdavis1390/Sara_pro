from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_benchmark import (
    NSBBenchmarkReport,
    run_nsb_benchmark,
    verify_nsb_benchmark_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic WS-NSB v0.6 G0/G1 instrumentation benchmark."
    )
    parser.add_argument(
        "--resolutions",
        default="8,16,32",
        help="comma-separated strictly increasing grid resolutions (default: 8,16,32)",
    )
    parser.add_argument("--h-exponent", type=float, default=0.005)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _parse_resolutions(value: str) -> tuple[int, ...]:
    try:
        resolutions = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("resolutions must be comma-separated integers") from exc
    if not resolutions:
        raise argparse.ArgumentTypeError("at least one resolution is required")
    return resolutions


def _serialize(report: NSBBenchmarkReport) -> str:
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
        report = NSBBenchmarkReport.model_validate(payload)
        if not verify_nsb_benchmark_report(report):
            print("INVALID")
            return 1
        print("VALID")
        return 0

    resolutions = _parse_resolutions(args.resolutions)
    report = run_nsb_benchmark(
        resolutions=resolutions,
        h_exponent=args.h_exponent,
    )
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

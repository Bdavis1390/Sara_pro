from __future__ import annotations

import argparse
import json
from pathlib import Path

from .programmable_boundary_benchmark import (
    ProgrammableBoundaryBenchmarkReport,
    run_programmable_boundary_benchmark,
    verify_programmable_boundary_benchmark_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic WS-QE-2026-EMB-001 programmable-boundary simulation benchmark."
    )
    parser.add_argument("--tile-count", type=int, default=8)
    parser.add_argument("--spacing", type=float, default=0.5)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _serialize(report: ProgrammableBoundaryBenchmarkReport) -> str:
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
        report = ProgrammableBoundaryBenchmarkReport.model_validate(payload)
        if not verify_programmable_boundary_benchmark_report(report):
            print("INVALID")
            return 1
        print("VALID")
        return 0

    report = run_programmable_boundary_benchmark(
        tile_count=args.tile_count,
        tile_spacing_wavelengths=args.spacing,
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

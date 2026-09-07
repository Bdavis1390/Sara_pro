from __future__ import annotations

import argparse
import json
from pathlib import Path

from .programmable_boundary_robustness import (
    ProgrammableBoundaryRobustnessReport,
    run_programmable_boundary_robustness,
    verify_programmable_boundary_robustness_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic WS-QE-2026-EMB-002 programmable-boundary robustness falsification gate."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _serialize(report: ProgrammableBoundaryRobustnessReport) -> str:
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
        report = ProgrammableBoundaryRobustnessReport.model_validate(payload)
        if not verify_programmable_boundary_robustness_report(report):
            print("INVALID")
            return 1
        print("VALID")
        return 0

    report = run_programmable_boundary_robustness()
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

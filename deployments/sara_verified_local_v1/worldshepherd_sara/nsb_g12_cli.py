from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_g12_adaptive_lorentz_control import NSBG12Report, run_nsb_g12_benchmark, verify_nsb_g12_report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run WS-NSB v1.7 G12 adaptive Lorentz-curl simulated control gate."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    return parser


def _serialize(report: NSBG12Report) -> str:
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
        report = NSBG12Report.model_validate(payload)
        if not verify_nsb_g12_report(report):
            print("INVALID")
            return 1
        if not report.acceptance.acceptance_pass:
            print("VALID-BUT-GATE-FAILED")
            return 2
        print("VALID")
        return 0

    report = run_nsb_g12_benchmark()
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

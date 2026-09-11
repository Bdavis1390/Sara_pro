from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_g14_geometry_em_forward_map import NSBG14Report, run_nsb_g14_benchmark, verify_nsb_g14_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or verify the WS-NSB v1.9 G14 benchmark")
    parser.add_argument("--output", type=Path, help="write a deterministic G14 JSON report")
    parser.add_argument("--verify", type=Path, help="verify an existing G14 JSON report")
    args = parser.parse_args()

    if args.verify is not None:
        report = NSBG14Report.model_validate_json(args.verify.read_text())
        if not verify_nsb_g14_report(report):
            raise SystemExit("G14 report digest verification failed")
        if not report.acceptance.acceptance_pass:
            raise SystemExit("G14 report did not pass acceptance")
        print(report.report_digest)
        return

    report = run_nsb_g14_benchmark()
    if not report.acceptance.acceptance_pass:
        raise SystemExit("G14 benchmark failed acceptance")
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()

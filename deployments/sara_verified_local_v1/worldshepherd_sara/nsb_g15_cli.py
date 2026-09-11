from __future__ import annotations

import argparse
import json
from pathlib import Path

from .nsb_g15_finite_geometry_em import NSBG15Report, run_nsb_g15_benchmark, verify_nsb_g15_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or verify the WS-NSB v2.0 G15 finite-geometry EM benchmark")
    parser.add_argument("--output", type=Path, help="write a deterministic G15 JSON report")
    parser.add_argument("--verify", type=Path, help="verify an existing G15 JSON report")
    args = parser.parse_args()

    if args.verify is not None:
        report = NSBG15Report.model_validate_json(args.verify.read_text())
        if not verify_nsb_g15_report(report):
            raise SystemExit("G15 report digest verification failed")
        if not report.acceptance.acceptance_pass:
            raise SystemExit("G15 report did not pass acceptance")
        print(report.report_digest)
        return

    report = run_nsb_g15_benchmark()
    if not report.acceptance.acceptance_pass:
        raise SystemExit("G15 benchmark failed acceptance")
    text = json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_evidence_profile_conformance import report_as_dict, run_profile_conformance


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Worldshepherd Quantum Mission Evidence Profile conformance suite")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_profile_conformance(repository_root=args.root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report_as_dict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{output}: {report.cases_passed}/{report.cases_total} cases passed")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assurance_benchmark import BenchmarkRun, evaluate_run, result_digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a Worldshepherd Assurance Composite Benchmark run."
    )
    parser.add_argument("input", help="Benchmark run JSON")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    run = BenchmarkRun.model_validate(payload)
    result = evaluate_run(run)
    wrapped = {
        "result": result,
        "result_sha256": result_digest(result),
    }
    rendered = json.dumps(wrapped, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

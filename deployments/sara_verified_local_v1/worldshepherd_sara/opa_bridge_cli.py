from __future__ import annotations

import argparse
import json
from pathlib import Path

from .opa_bridge import evaluate_boolean_policy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a bounded boolean OPA policy decision and emit a Worldshepherd evidence receipt."
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8181/v1/data/worldshepherd/allow",
    )
    parser.add_argument("--input", required=True, help="JSON file containing the OPA input document")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"input JSON file not found: {input_path}")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input JSON must be an object")

    receipt = evaluate_boolean_policy(
        endpoint=args.endpoint,
        input_document=payload,
        allow_remote=args.allow_remote,
        timeout_seconds=args.timeout_seconds,
    )
    rendered = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if receipt["opa_result"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

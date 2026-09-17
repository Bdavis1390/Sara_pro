from __future__ import annotations

import argparse
import json
from pathlib import Path

from .trace_context import extract_w3c_trace_context, receipt_sha256


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate W3C Trace Context and emit a bounded Worldshepherd correlation receipt."
    )
    parser.add_argument("--traceparent", required=True)
    parser.add_argument("--tracestate")
    parser.add_argument("--evidence-sha256")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    receipt = extract_w3c_trace_context(
        traceparent=args.traceparent,
        tracestate=args.tracestate,
        evidence_sha256=args.evidence_sha256,
    )
    result = {"receipt": receipt, "receipt_sha256": receipt_sha256(receipt)}
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .echo_checkpoint_verify import EchoCheckpointVerificationError, verify_chain


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Independently verify an ordered Worldshepherd ECHO checkpoint chain."
    )
    parser.add_argument(
        "--expected-fingerprint",
        required=True,
        help="Pinned SHA-256 fingerprint of the trusted Ed25519 checkpoint public key.",
    )
    parser.add_argument(
        "--output",
        help="Optional path for the JSON verification summary; stdout is always emitted.",
    )
    parser.add_argument(
        "bundles",
        nargs="+",
        help="Checkpoint bundle JSON files in chain order. Reordering is an error.",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        bundles = []
        for value in args.bundles:
            path = Path(value)
            body = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(body, dict):
                raise EchoCheckpointVerificationError(
                    f"checkpoint bundle is not a JSON object: {path}"
                )
            bundles.append(body)
        summary = verify_chain(bundles, args.expected_fingerprint)
    except (OSError, json.JSONDecodeError, EchoCheckpointVerificationError) as exc:
        print(f"ECHO checkpoint verification FAILED: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(summary, sort_keys=True, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

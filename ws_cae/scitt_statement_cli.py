from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scitt_statement import build_chain_statement, canonical_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an RFC 9943-oriented WS-CAE transparency statement payload")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--observed-at")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        patch = json.loads(args.patch.read_text(encoding="utf-8"))
        statement = build_chain_statement(patch, args.issuer, args.observed_at)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"spec": "WS-CAE-SCITT-STATEMENT-1", "input_error": str(exc)}, sort_keys=True))
        return 2

    if args.pretty:
        print(json.dumps(statement, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(canonical_json(statement).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

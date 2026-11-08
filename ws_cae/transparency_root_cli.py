from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scitt_statement import build_chain_statement
from .transparency_root import build_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic DATL Merkle root from WS-CAE chain patches")
    parser.add_argument("patches", nargs="+", type=Path)
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    try:
        statements = []
        for path in args.patches:
            patch = json.loads(path.read_text(encoding="utf-8"))
            statements.append(build_chain_statement(patch, args.issuer, args.observed_at))
        output = build_root(statements)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"spec": "WS-CAE-DATL-ROOT-1", "input_error": str(exc)}, sort_keys=True))
        return 2

    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

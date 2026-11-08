from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli import InputError, _json
from .continuity_adapter import from_chain_patch
from .continuity_manifest import envelope
from .patch_cli import parse_patch


def run(path: Path, *, version: str, as_of: str) -> dict:
    patch = parse_patch(_json(path, "patch"))
    return envelope(from_chain_patch(patch, version=version, as_of=as_of))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a content-addressed WS-CAE continuity manifest")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--version", default="1")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run(args.patch, version=args.version, as_of=args.as_of)
    except InputError as exc:
        print(json.dumps({"spec":"WS-CAE-CONTINUITY-MANIFEST-1","input_error":str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

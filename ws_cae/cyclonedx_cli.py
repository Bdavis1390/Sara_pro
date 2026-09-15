"""CLI that exports a WS-CAE crypto-system patch as CycloneDX 1.7 JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli import InputError
from .crypto_system_cli import parse_system_patch
from .cyclonedx_export import export_cyclonedx


def run(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"unable to read crypto-system patch: {exc}") from exc
    patch = parse_system_patch(raw)
    return export_cyclonedx(patch)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export WS-CAE crypto-system patch as CycloneDX 1.7")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.patch)
    except InputError as exc:
        print(json.dumps({"input_error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

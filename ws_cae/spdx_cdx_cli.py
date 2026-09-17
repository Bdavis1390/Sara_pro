from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cyclonedx_cli import run as run_cyclonedx
from .spdx_bridge import to_spdx


def _props(items: list[dict]) -> dict[str, str]:
    return {
        str(item.get("name", "")): str(item.get("value", ""))
        for item in items
        if item.get("name")
    }


def run(path: Path) -> dict:
    bom = run_cyclonedx(path)
    root = bom["metadata"]["component"]
    entries = []
    for component in bom.get("components", []):
        values = _props(component.get("properties", []))
        values["name"] = component.get("name", component.get("bom-ref", "component"))
        entries.append(values)
    return to_spdx(root["name"], entries, _props(root.get("properties", [])))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE SPDX 3.0.1 bridge")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        output = run(args.patch)
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(output, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

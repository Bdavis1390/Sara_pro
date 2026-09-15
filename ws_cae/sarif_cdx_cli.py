from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cyclonedx_cli import run as run_cyclonedx

SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"


def _props(items: list[dict]) -> dict[str, str]:
    return {str(x.get("name")): str(x.get("value")) for x in items if x.get("name")}


def _source_uri(path: Path) -> str:
    parts = path.as_posix().split("/")
    if "ws_cae" in parts:
        return "/".join(parts[parts.index("ws_cae") :])
    return path.name


def run(path: Path) -> dict:
    bom = run_cyclonedx(path)
    root = bom["metadata"]["component"]
    source_uri = _source_uri(path)
    results = []
    for component in bom.get("components", []):
        props = _props(component.get("properties", []))
        state = props.get("ws-cae:readiness-state", "UNASSESSED")
        critical = props.get("ws-cae:critical", "false") == "true"
        if not critical or state == "PQ_DEPLOYED":
            continue
        results.append(
            {
                "ruleId": "WSCAE001",
                "level": "warning" if state != "UNASSESSED" else "error",
                "message": {
                    "text": f"{component.get('name', 'component')} is a critical declared dependency with readiness state {state}."
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": source_uri,
                                "uriBaseId": "%SRCROOT%",
                            }
                        }
                    }
                ],
                "properties": {
                    "ws-cae:role": props.get("ws-cae:role", "UNSPECIFIED"),
                    "ws-cae:readiness-state": state,
                    "ws-cae:asset": root.get("name", "asset"),
                    "ws-cae:evidence-source": source_uri,
                },
            }
        )
    return {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "WS-CAE",
                        "informationUri": "https://github.com/Bdavis1390/Sara_pro",
                        "rules": [
                            {
                                "id": "WSCAE001",
                                "name": "CriticalDependencyReadiness",
                                "shortDescription": {"text": "Critical dependency is not fully deployed for the evaluated migration state"},
                            }
                        ],
                    }
                },
                "results": results,
            }
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE SARIF 2.1.0 bridge")
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

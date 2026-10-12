from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from .cyclonedx_cli import run as run_cyclonedx

SOURCE = "https://worldshepherd.dev/ws-cae"
EVENT_TYPE = "dev.worldshepherd.wscae.readiness.assessed"


def _props(items: list[dict]) -> dict[str, str]:
    return {str(item.get("name")): str(item.get("value")) for item in items if item.get("name")}


def run(path: Path) -> dict:
    bom = run_cyclonedx(path)
    root = bom["metadata"]["component"]
    properties = _props(root.get("properties", []))
    components = []
    for component in bom.get("components", []):
        props = _props(component.get("properties", []))
        components.append(
            {
                "name": component.get("name", "component"),
                "role": props.get("ws-cae:role", "UNSPECIFIED"),
                "readiness_state": props.get("ws-cae:readiness-state", "UNASSESSED"),
                "critical": props.get("ws-cae:critical", "false") == "true",
                "evidence_documented": props.get("ws-cae:evidence-documented", "false") == "true",
            }
        )
    identity = json.dumps({"asset": root.get("name"), "components": components}, sort_keys=True, separators=(",", ":"))
    return {
        "specversion": "1.0",
        "id": sha256(identity.encode("utf-8")).hexdigest(),
        "source": SOURCE,
        "type": EVENT_TYPE,
        "subject": str(root.get("name", "asset")),
        "time": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "datacontenttype": "application/json",
        "data": {
            "asset": root.get("name", "asset"),
            "system_state": properties.get("ws-cae:system-state", "UNASSESSED"),
            "weakest_readiness_state": properties.get("ws-cae:weakest-readiness-state", "UNASSESSED"),
            "components": components,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE CloudEvents 1.0 bridge")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    try:
        event = run(args.patch)
    except (KeyError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(event, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

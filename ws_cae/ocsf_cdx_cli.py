from __future__ import annotations

import argparse
import json
import time
from hashlib import sha256
from pathlib import Path

from .cyclonedx_cli import run as run_cyclonedx


def _props(items: list[dict]) -> dict[str, str]:
    return {str(item.get("name")): str(item.get("value")) for item in items if item.get("name")}


def run(path: Path) -> dict:
    bom = run_cyclonedx(path)
    root = bom["metadata"]["component"]
    root_props = _props(root.get("properties", []))
    asset = str(root.get("name", "asset"))
    components = []
    blockers = []
    for component in bom.get("components", []):
        props = _props(component.get("properties", []))
        item = {
            "name": component.get("name", "component"),
            "role": props.get("ws-cae:role", "UNSPECIFIED"),
            "readiness_state": props.get("ws-cae:readiness-state", "UNASSESSED"),
            "critical": props.get("ws-cae:critical", "false") == "true",
        }
        components.append(item)
        if item["critical"] and item["readiness_state"] != "PQ_DEPLOYED":
            blockers.append(f"{item['role']}:{item['name']}")

    identity = json.dumps({"asset": asset, "components": components}, sort_keys=True, separators=(",", ":"))
    finding_uid = sha256(identity.encode("utf-8")).hexdigest()
    weakest = root_props.get("ws-cae:weakest-readiness-state", "UNASSESSED")
    severity_id = 4 if weakest in {"UNASSESSED", "CLASSICAL_DEPENDENCY"} else 3
    now_ms = int(time.time() * 1000)
    return {
        "activity_id": 1,
        "category_uid": 2,
        "class_uid": 2004,
        "type_uid": 200401,
        "severity_id": severity_id,
        "time": now_ms,
        "metadata": {
            "version": "1.8.0",
            "product": {
                "name": "WS-CAE",
                "vendor_name": "Worldshepherd",
                "version": "0.1.0-research",
            },
        },
        "finding_info": {
            "uid": finding_uid,
            "title": f"WS-CAE dependency readiness finding for {asset}",
            "desc": f"Weakest declared critical dependency readiness state: {weakest}",
        },
        "is_alert": bool(blockers),
        "status_id": 1,
        "message": f"WS-CAE assessment for {asset}: {root_props.get('ws-cae:system-state', 'UNASSESSED')}",
        "unmapped": {
            "ws_cae_asset": asset,
            "ws_cae_system_state": root_props.get("ws-cae:system-state", "UNASSESSED"),
            "ws_cae_weakest_readiness_state": weakest,
            "ws_cae_blocking_components": blockers,
            "ws_cae_components": components,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WS-CAE OCSF 1.8 Detection Finding bridge")
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

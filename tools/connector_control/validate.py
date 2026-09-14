#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.connector_control import ConnectorControlPlane


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "worldshepherd_connectors.v2.json"


def main() -> int:
    control = ConnectorControlPlane(MANIFEST)
    result = {
        "validation": control.validate_manifest(),
        "health": control.health_snapshot(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

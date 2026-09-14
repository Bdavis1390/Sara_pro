#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worldshepherd_sara.connector_control import ConnectorControlPlane

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

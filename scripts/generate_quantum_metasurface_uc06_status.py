#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from worldshepherd_sara.quantum_metasurface_uc06 import retained_uc06_status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = {
        "schema_version": "1.0",
        "project_id": "WS-METASURFACE",
        "evidence_class": "retained_precalibration_status_not_raw_solver_evidence",
        "decision": asdict(retained_uc06_status()),
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from worldshepherd_sara.quantum_mission_readiness import current_quantum_mission_calibration


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Worldshepherd quantum mission-readiness calibration")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    results = current_quantum_mission_calibration()
    payload = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "system": "Worldshepherd Mission Readiness Calibration",
        "scope": "quantum project lanes",
        "claim_control": (
            "Internal evidence-governed engineering calibration only; not TRL, certification, deployment authority, "
            "combat suitability, safety approval, or proof of quantum advantage."
        ),
        "results": [asdict(row) for row in results],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

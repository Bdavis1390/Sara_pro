from __future__ import annotations

import argparse
import json
import platform
import sys

from worldshepherd_sara.rmabm_provenance import measure_synthetic_scale


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an unclassified synthetic W-RMABM scale measurement. Results are environment-specific."
    )
    parser.add_argument("--track-pairs", type=int, default=100)
    args = parser.parse_args()

    result = measure_synthetic_scale(track_pair_count=args.track_pairs)
    payload = {
        "evidence_state": "SYNTHETIC_INTERNAL_MEASUREMENT_ONLY",
        "claims_boundary": (
            "Not an operational missile-warning/tracking benchmark and not BAE/SDA/SSC/Space Force/Golden Dome validation."
        ),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "measurement": result.model_dump(mode="json"),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_acquisition_request import build_all_acquisition_requests


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate QRF partner/lab acquisition request packages")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    requests = build_all_acquisition_requests()
    payload = {
        "schema_version": "1.0",
        "system": "Worldshepherd QRF Evidence Acquisition Requests",
        "request_count": len(requests),
        "requests": [asdict(request) for request in requests],
        "claim_control": (
            "These are request templates generated from QRF campaign gates. They contain no external evidence and cannot raise mission readiness."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

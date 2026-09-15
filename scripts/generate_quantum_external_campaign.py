from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_external_campaign import campaigns_as_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate stage-locked QRF external evidence acquisition campaign")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = campaigns_as_dict()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

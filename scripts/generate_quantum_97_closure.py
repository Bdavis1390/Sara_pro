from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_closure import generate_closure_packages


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate closure packages for every quantum lane below 97")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = generate_closure_packages()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

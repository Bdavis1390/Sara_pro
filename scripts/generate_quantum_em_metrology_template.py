from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldshepherd_sara.quantum_em_metrology import em_metrology_template_as_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deliberately incomplete WS-EM-PROPULSION materials/metrology template")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(em_metrology_template_as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

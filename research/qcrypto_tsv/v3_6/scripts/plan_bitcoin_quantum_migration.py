#!/usr/bin/env python3
"""Build a local Bitcoin quantum-risk migration manifest from an offline UTXO JSON file."""
from __future__ import annotations

import argparse
import json
import pathlib

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import UtxoRecord, build_migration_manifest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON array of UTXO records")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    raw = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("input must be a JSON array")
    records = [UtxoRecord(**item) for item in raw]
    manifest = build_migration_manifest(records)
    pathlib.Path(args.output).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("utxos:", manifest["totals"]["utxo_count"])
    print("long_or_reuse_exposed_sat:", manifest["totals"]["long_or_reuse_exposed_sat"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

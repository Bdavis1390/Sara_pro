#!/usr/bin/env python3
"""Emit a machine-readable WS-QPOS-1 bounded preservation proof report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from security.qcrypto.qpos_preservation import run_bounded_preservation_proof


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="qpos-proof.json")
    args = parser.parse_args()

    report = run_bounded_preservation_proof().to_dict()
    payload = {
        "schema": "WS-QPOS-1-PRESERVATION-PROOF-V1",
        "proof_scope": "BOUNDED_MODEL_ONLY",
        "post_quantum_primitive_security": "ASSUMED_NOT_PROVEN_HERE",
        "production_consensus_security": "NOT_PROVEN_HERE",
        "report": report,
    }
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    payload["evidence_sha256"] = digest

    path = Path(args.output)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if report["proof_status"] != "PASS":
        return 1
    if report["claim_state"] != "BOUNDED_MODEL_PROOF_OF_POS_MIGRATION_PRESERVATION":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

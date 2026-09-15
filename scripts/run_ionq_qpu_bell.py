#!/usr/bin/env python3
"""Run QRF-BELL-001 on IonQ hardware with runtime-only credentials."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_ionq import build_sara_qpu_external_evidence, run_bell_on_ionq_hardware


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, help="Explicit IonQ qpu.* backend, e.g. qpu.forte-1")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--output", required=True)
    parser.add_argument("--campaign-gate-id", default="SARA-QRF-EXT-01")
    args = parser.parse_args()

    token = os.environ.get("IONQ_API_KEY", "")
    if not token:
        raise SystemExit("IONQ_API_KEY must be injected in the process environment; do not pass it on the command line")

    result = run_bell_on_ionq_hardware(token=token, backend=args.backend, shots=args.shots)
    evidence = build_sara_qpu_external_evidence(result, campaign_gate_id=args.campaign_gate_id)
    payload = {
        "provider_result": result.to_dict(),
        "provider_neutral_record": asdict(result.provider_record()),
        "external_evidence_record": asdict(evidence),
        "claim_control": "This file records one IonQ hardware execution only; it does not establish reproduction, quantum advantage, mission readiness, or hardware ownership.",
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

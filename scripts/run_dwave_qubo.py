#!/usr/bin/env python3
"""Run a governed frozen QUBO on a D-Wave QPU and emit typed QRF evidence."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_dwave import (
    build_dwave_mission_optimization_evidence,
    run_qubo_on_dwave_hardware,
)
from worldshepherd_sara.quantum_external_evidence import validate_external_evidence


def _load_manifest(path: Path) -> tuple[dict, dict[tuple[str, str], float]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("qubo_terms")
    if not isinstance(rows, list) or not rows:
        raise ValueError("manifest.qubo_terms must be a non-empty list")
    qubo: dict[tuple[str, str], float] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not {"u", "v", "weight"}.issubset(row):
            raise ValueError(f"qubo_terms[{index}] requires u, v and weight")
        key = (str(row["u"]), str(row["v"]))
        qubo[key] = qubo.get(key, 0.0) + float(row["weight"])
    return payload, qubo


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a frozen Worldshepherd QUBO on D-Wave QPU hardware")
    parser.add_argument("--manifest", required=True, help="Governed JSON QUBO/mission manifest")
    parser.add_argument("--output", required=True)
    parser.add_argument("--num-reads", type=int, default=1000)
    parser.add_argument("--solver", default=os.getenv("DWAVE_SOLVER"))
    parser.add_argument("--cost-usd", type=float, default=None)
    args = parser.parse_args()

    token = os.getenv("DWAVE_API_TOKEN", "")
    if not token.strip():
        raise SystemExit("DWAVE_API_TOKEN is required at runtime and must not be stored in the manifest/repository")

    manifest_path = Path(args.manifest)
    manifest, qubo = _load_manifest(manifest_path)
    required = (
        "project_id",
        "campaign_gate_id",
        "classical_baseline_digest",
        "instance_family_digest",
        "objective_definition",
        "constraint_definition",
    )
    missing = [name for name in required if not str(manifest.get(name, "")).strip()]
    if missing:
        raise SystemExit(f"manifest missing required fields: {missing}")

    cost_usd = args.cost_usd
    if cost_usd is None:
        raw_cost = manifest.get("cost_usd")
        if raw_cost is None:
            raise SystemExit("--cost-usd or manifest.cost_usd is required; do not invent execution cost")
        cost_usd = float(raw_cost)

    result = run_qubo_on_dwave_hardware(
        qubo,
        token=token,
        num_reads=args.num_reads,
        solver_name=args.solver,
        label=str(manifest.get("label", "Worldshepherd QRF annealing benchmark")),
    )
    evidence = build_dwave_mission_optimization_evidence(
        result,
        project_id=str(manifest["project_id"]),
        campaign_gate_id=str(manifest["campaign_gate_id"]),
        classical_baseline_digest=str(manifest["classical_baseline_digest"]),
        instance_family_digest=str(manifest["instance_family_digest"]),
        objective_definition=str(manifest["objective_definition"]),
        constraint_definition=str(manifest["constraint_definition"]),
        cost_usd=float(cost_usd),
    )
    intake = validate_external_evidence(evidence)
    if not intake.accepted_for_intake:
        raise SystemExit(f"D-Wave evidence failed structural intake: {intake.reasons}")

    output_payload = {
        "schema_version": "1.0",
        "manifest_path": str(manifest_path),
        "hardware_result": result.to_dict(),
        "external_evidence_record": asdict(evidence),
        "intake_decision": asdict(intake),
        "claim_control": (
            "A successful runner output is structurally typed D-Wave annealing evidence only. It does not close the named campaign gate "
            "unless the supplied frozen mission instance/baseline is itself valid for that gate and the package passes the normal QRF ingest, "
            "identified-human technical review, and separate canonical state-change process."
        ),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output_payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"{out}: solver={result.solver_name} modality={result.modality} project={evidence.project_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

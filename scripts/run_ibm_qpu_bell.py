#!/usr/bin/env python3
"""Execute QRF-BELL-001 on IBM quantum hardware and emit gate-valid evidence."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import json
import os
from pathlib import Path

from worldshepherd_sara.quantum_external_campaign import build_external_campaigns, evaluate_campaign
from worldshepherd_sara.quantum_external_evidence import validate_external_evidence
from worldshepherd_sara.quantum_ibm import build_sara_qpu_external_evidence, run_bell_on_ibm_hardware


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=os.getenv("IBM_QUANTUM_BACKEND"))
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--plan-name", default=os.getenv("IBM_QUANTUM_PLAN_NAME"))
    parser.add_argument("--cost-usd", type=float, default=_env_float("IBM_QUANTUM_JOB_COST_USD"))
    parser.add_argument(
        "--output",
        default=".qrf-artifacts/qrf_bell_001_ibm_qpu_evidence.json",
    )
    args = parser.parse_args()

    token = os.getenv("IBM_QUANTUM_TOKEN", "")
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    if not args.plan_name:
        raise SystemExit("--plan-name or IBM_QUANTUM_PLAN_NAME is required; use 'open' only when the job is intended for IBM Open Plan")
    cost_usd = args.cost_usd
    if cost_usd is None and args.plan_name.strip().lower() == "open":
        cost_usd = 0.0
    if cost_usd is None:
        raise SystemExit("--cost-usd or IBM_QUANTUM_JOB_COST_USD is required for non-Open-Plan execution")

    result = run_bell_on_ibm_hardware(
        token=token,
        instance=instance,
        backend_name=args.backend,
        shots=args.shots,
        optimization_level=args.optimization_level,
        expected_plan=args.plan_name,
    )
    evidence = build_sara_qpu_external_evidence(
        result,
        plan_name=args.plan_name,
        cost_usd=cost_usd,
    )
    intake = validate_external_evidence(evidence)
    if not intake.accepted_for_intake:
        raise SystemExit(f"IBM QPU evidence failed structural intake: {intake.reasons}")

    sara_campaign = next(row for row in build_external_campaigns() if row.project_id == "SARA-QRF")
    campaign = evaluate_campaign(sara_campaign, [evidence])
    if campaign.achieved_stage != "single_external_hardware":
        first_gate = campaign.gate_evaluations[0] if campaign.gate_evaluations else None
        reasons = () if first_gate is None else first_gate.reasons
        raise SystemExit(f"IBM QPU evidence did not close SARA-QRF-EXT-01: {reasons}")

    payload = {
        "schema_version": "1.1",
        "benchmark_id": "QRF-BELL-001",
        "hardware_result": result.to_dict(),
        "external_evidence_record": asdict(evidence),
        "intake_decision": asdict(intake),
        "campaign_evaluation": asdict(campaign),
        "claim_control": (
            "This bundle closes only the structural SARA-QRF first external-hardware acquisition gate when all recorded fields are genuine. "
            "The IBM instance and plan are service-resolved and verified before QPU submission. "
            "It does not establish quantum advantage, reproduced hardware evidence, 97 mission readiness, or deployment authority."
        ),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(
        f"{out}: backend={result.backend} instance={result.instance} plan={result.instance_plan} "
        f"job_id={result.job_id} gate=SARA-QRF-EXT-01"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Conservative PRIME authorization gate for WS-QPHONON L2.

The gate consumes already-estimated evidence. It does not perform Bayesian
inference and does not assert physical capability. A PASS means only that the
software screening rules are satisfied and the proposal may advance to a
separate human-approval gate.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GateDecision:
    authorized: bool
    disposition: str
    reasons: list[str]
    requires_human_approval: bool


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def evaluate(config: dict[str, Any], evidence: dict[str, Any]) -> GateDecision:
    reasons: list[str] = []
    prime = config["prime_authorization"]
    requirements = prime["coherent_transfer_attempt_requires"]
    p_max = float(prime["posterior_violation_probability_max"])

    cooperativity = evidence.get("cooperativity_ct2")
    if not _finite_number(cooperativity) or float(cooperativity) < 0.0:
        reasons.append("COOPERATIVITY_INVALID")
    elif float(cooperativity) < float(requirements["cooperativity_ct2_min"]):
        reasons.append("COOPERATIVITY_BELOW_MINIMUM")

    temperature = evidence.get("device_temperature_k_mean")
    if not _finite_number(temperature) or float(temperature) < 0.0:
        reasons.append("TEMPERATURE_INVALID")
    elif float(temperature) > float(requirements["temperature_k_max"]):
        reasons.append("TEMPERATURE_MEAN_ABOVE_SCREEN")

    for field, invalid_reason, risk_reason in (
        (
            "temperature_violation_probability",
            "TEMPERATURE_POSTERIOR_RISK_INVALID",
            "TEMPERATURE_POSTERIOR_RISK_TOO_HIGH",
        ),
        (
            "orbital_leakage_violation_probability",
            "ORBITAL_LEAKAGE_POSTERIOR_RISK_INVALID",
            "ORBITAL_LEAKAGE_POSTERIOR_RISK_TOO_HIGH",
        ),
    ):
        value = evidence.get(field)
        if not _finite_number(value) or not 0.0 <= float(value) <= 1.0:
            reasons.append(invalid_reason)
        elif float(value) > p_max:
            reasons.append(risk_reason)

    required_true = (
        ("parameter_confidence_gates_pass", "PARAMETER_CONFIDENCE_GATE_FAILED"),
        ("model_holdout_validation_pass", "HOLDOUT_VALIDATION_FAILED"),
        ("claims_state_allows_experiment", "CLAIMS_STATE_BLOCKS_EXPERIMENT"),
        ("model_discrepancy_pass", "MODEL_DISCREPANCY_OUT_OF_BOUNDS"),
        ("mechanical_linewidth_in_envelope", "MECHANICAL_LINEWIDTH_OUT_OF_ENVELOPE"),
        ("detuning_in_envelope", "DETUNING_OUT_OF_ENVELOPE"),
    )
    for field, reason in required_true:
        if evidence.get(field) is not True:
            reasons.append(reason)

    authorized = not reasons
    return GateDecision(
        authorized=authorized,
        disposition="READY_FOR_HUMAN_APPROVAL" if authorized else "CHARACTERIZE_OR_ABORT",
        reasons=reasons,
        requires_human_approval=authorized,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", help="JSON evidence snapshot")
    parser.add_argument(
        "--config",
        default="config/ws_qphonon_l2_v0_1.json",
        help="WS-QPHONON governed config",
    )
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    decision = evaluate(config, evidence)
    print(json.dumps(asdict(decision), indent=2, sort_keys=True))
    return 0 if decision.authorized else 2


if __name__ == "__main__":
    raise SystemExit(main())

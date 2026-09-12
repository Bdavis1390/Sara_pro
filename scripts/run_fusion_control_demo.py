#!/usr/bin/env python3
"""Run one simulator-only Worldshepherd fusion-control cycle."""

import json
from dataclasses import asdict

from worldshepherd_sara.fusion_control import SensorSample, run_simulated_control_cycle


if __name__ == "__main__":
    upper = SensorSample(
        timestamp=1_000.000,
        shot_id="demo-001",
        diagnostic="upper_divertor_visible_emission",
        value=112.0,
        unit="arb",
        uncertainty=1.0,
        valid=True,
        quality="demo",
        provenance="synthetic:demo-001:upper",
    )
    lower = SensorSample(
        timestamp=1_000.000,
        shot_id="demo-001",
        diagnostic="lower_divertor_visible_emission",
        value=88.0,
        unit="arb",
        uncertainty=1.0,
        valid=True,
        quality="demo",
        provenance="synthetic:demo-001:lower",
    )

    result = run_simulated_control_cycle(upper, lower)
    print(json.dumps({
        "state": asdict(result.state),
        "proposal": asdict(result.proposal),
        "decision": asdict(result.decision),
        "ledger_ok": result.ledger_ok,
        "ledger_reason": result.ledger_reason,
        "hardware_interface": "disabled",
    }, indent=2, sort_keys=True))

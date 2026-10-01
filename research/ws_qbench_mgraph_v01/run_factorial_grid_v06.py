"""Reproducible runner for the WS-QBENCH-MGRAPH v0.6 factorial grid.

This runner serializes only numerical diagnostics. It does not resolve the v0.5
source-lock blockers and must not be used to claim exact Figure 4 reproduction.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .factorial_interaction_v06 import factorial_interaction_ablation


def build_grid(
    *,
    nmax_values=(40, 60, 80),
    etas=(0.5, 1.0, 2.0),
    reference_ratio=0.5,
    target_ratios=(2.0, 5.0),
    repetitions=30,
    eigenstates=30,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for nmax in nmax_values:
        for eta in etas:
            for target_ratio in target_ratios:
                seed = 10000 + int(nmax) + int(float(eta) * 100) + int(float(target_ratio) * 10)
                rows.append(
                    {
                        "nmax": int(nmax),
                        "eta": float(eta),
                        "reference_ratio": float(reference_ratio),
                        "target_ratio": float(target_ratio),
                        "seed": seed,
                        "result": factorial_interaction_ablation(
                            nmax=int(nmax),
                            eta=float(eta),
                            reference_ratio=float(reference_ratio),
                            target_ratio=float(target_ratio),
                            omega0=1.0,
                            h_parallel_over_omega0=0.0,
                            h0_over_omega0=0.0,
                            eigenstates=int(eigenstates),
                            repetitions=int(repetitions),
                            seed=seed,
                        ),
                    }
                )
    return {
        "schema": "ws_qbench_mgraph.factorial_interaction.v0.6.grid",
        "claim_state": "SIMULATED ONLY",
        "exact_figure_reproduction_claimed": False,
        "design": {
            "nmax": [int(x) for x in nmax_values],
            "etas": [float(x) for x in etas],
            "reference_ratio": float(reference_ratio),
            "target_ratios": [float(x) for x in target_ratios],
            "omega0": 1.0,
            "h_parallel_over_omega0": 0.0,
            "h0_over_omega0": 0.0,
            "eigenstates": int(eigenstates),
            "stochastic_repetitions": int(repetitions),
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("factorial_grid_v06.json"))
    parser.add_argument("--repetitions", type=int, default=30)
    args = parser.parse_args()
    payload = build_grid(repetitions=args.repetitions)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

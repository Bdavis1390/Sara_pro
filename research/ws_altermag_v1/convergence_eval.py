from __future__ import annotations

import json
import math
from pathlib import Path


HARTREE_TO_MEV = 27211.386245988
ATOMS_PER_CRSB_CELL = 4


def compare_metrics(
    lower: dict,
    higher: dict,
    *,
    energy_mev_per_atom_max: float,
    cr_moment_muB_delta_max: float,
) -> dict:
    e0 = lower.get("final_total_energy_ha_per_cell")
    e1 = higher.get("final_total_energy_ha_per_cell")
    m0 = lower.get("cr_local_moment_magnitudes_muB") or []
    m1 = higher.get("cr_local_moment_magnitudes_muB") or []

    energy_available = e0 is not None and e1 is not None
    moments_available = bool(m0) and len(m0) == len(m1)

    energy_delta = (
        abs(float(e1) - float(e0)) * HARTREE_TO_MEV / ATOMS_PER_CRSB_CELL
        if energy_available
        else None
    )
    moment_deltas = (
        [abs(float(b) - float(a)) for a, b in zip(m0, m1)]
        if moments_available
        else []
    )
    moment_delta_max = max(moment_deltas) if moment_deltas else None

    energy_pass = bool(
        energy_delta is not None and energy_delta <= energy_mev_per_atom_max
    )
    moment_pass = bool(
        moment_delta_max is not None and moment_delta_max <= cr_moment_muB_delta_max
    )

    return {
        "energy_available": energy_available,
        "moments_available": moments_available,
        "energy_delta_meV_per_atom": energy_delta,
        "cr_local_moment_deltas_muB": moment_deltas,
        "cr_local_moment_delta_max_muB": moment_delta_max,
        "energy_threshold_meV_per_atom": energy_mev_per_atom_max,
        "cr_moment_threshold_muB": cr_moment_muB_delta_max,
        "energy_pass": energy_pass,
        "moment_pass": moment_pass,
        "pass": energy_pass and moment_pass,
        "decision": "ADVANCE" if energy_pass and moment_pass else "HOLD",
        "claim_boundary": (
            "Convergence compares adjacent numerical settings only. A convergence pass does not "
            "validate the material model against experiment."
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("lower", type=Path)
    parser.add_argument("higher", type=Path)
    parser.add_argument("--energy-mev-per-atom-max", type=float, default=1.0)
    parser.add_argument("--cr-moment-delta-max", type=float, default=0.01)
    args = parser.parse_args()

    lower = json.loads(args.lower.read_text(encoding="utf-8"))
    higher = json.loads(args.higher.read_text(encoding="utf-8"))
    result = compare_metrics(
        lower,
        higher,
        energy_mev_per_atom_max=args.energy_mev_per_atom_max,
        cr_moment_muB_delta_max=args.cr_moment_delta_max,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

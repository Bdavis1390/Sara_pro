from __future__ import annotations

import json
from pathlib import Path

from .convergence_eval import compare_metrics
from .convergence_b000 import DEFAULT_PLAN


BASIS_LABELS = (
    "basis-rgkmax-6.0",
    "basis-rgkmax-7.0",
    "basis-rgkmax-8.0",
)


def _case_for_label(plan: dict, label: str) -> dict:
    rgk = float(label.rsplit("-", 1)[1])
    return {
        "label": label,
        "kgrid": list(plan["basis_convergence"]["fixed_kgrid"]),
        "rgkmax": rgk,
    }


def _load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_valid(summary: dict) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not summary.get("energy_convergence_target_achieved"):
        blockers.append("SCF_ENERGY_TARGET_NOT_ACHIEVED")
    if summary.get("final_total_energy_ha_per_cell") is None:
        blockers.append("TOTAL_ENERGY_MISSING")
    moments = summary.get("cr_local_moment_magnitudes_muB") or []
    if len(moments) != 2:
        blockers.append("TWO_CR_LOCAL_MOMENTS_REQUIRED")
    return (not blockers, blockers)


def choose_next_basis_case(
    summaries: dict[str, dict],
    plan_path: Path = DEFAULT_PLAN,
) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    thresholds = plan["basis_convergence"]["acceptance"]

    # Never skip an unexecuted earlier case.
    for label in BASIS_LABELS:
        if label not in summaries:
            earlier = BASIS_LABELS[: BASIS_LABELS.index(label)]
            invalid = []
            for prev in earlier:
                ok, blockers = _summary_valid(summaries[prev])
                if not ok:
                    invalid.append({"label": prev, "blockers": blockers})
            if invalid:
                return {
                    "decision": "HOLD",
                    "reason": "EARLIER_CASE_INVALID",
                    "invalid_cases": invalid,
                    "next_case": None,
                }
            return {
                "decision": "RUN_NEXT_BASIS_CASE",
                "reason": "SEQUENCE_INCOMPLETE",
                "next_case": _case_for_label(plan, label),
            }

    invalid = []
    for label in BASIS_LABELS:
        ok, blockers = _summary_valid(summaries[label])
        if not ok:
            invalid.append({"label": label, "blockers": blockers})
    if invalid:
        return {
            "decision": "HOLD",
            "reason": "CASE_INVALID",
            "invalid_cases": invalid,
            "next_case": None,
        }

    # Convergence decision is based on the highest-resolution adjacent pair.
    # rgkmax=6 is retained as the coarse trend anchor; rgkmax=7 -> 8 must pass.
    final_compare = compare_metrics(
        summaries["basis-rgkmax-7.0"],
        summaries["basis-rgkmax-8.0"],
        energy_mev_per_atom_max=float(thresholds["total_energy_meV_per_atom_delta_max"]),
        cr_moment_muB_delta_max=float(thresholds["Cr_local_moment_muB_delta_max"]),
    )

    coarse_compare = compare_metrics(
        summaries["basis-rgkmax-6.0"],
        summaries["basis-rgkmax-7.0"],
        energy_mev_per_atom_max=float(thresholds["total_energy_meV_per_atom_delta_max"]),
        cr_moment_muB_delta_max=float(thresholds["Cr_local_moment_muB_delta_max"]),
    )

    if not final_compare["pass"]:
        return {
            "decision": "HOLD",
            "reason": "BASIS_NOT_CONVERGED_AT_RGKMAX_8",
            "coarse_6_to_7": coarse_compare,
            "final_7_to_8": final_compare,
            "next_case": None,
        }

    return {
        "decision": "BASIS_GATE_PASS",
        "reason": "RGKMAX_7_TO_8_WITHIN_THRESHOLDS",
        "coarse_6_to_7": coarse_compare,
        "final_7_to_8": final_compare,
        "accepted_rgkmax": 8.0,
        "next_stage": "KGRID_CONVERGENCE",
        "claim_boundary": (
            "BASIS_GATE_PASS establishes numerical basis convergence under the declared "
            "engineering thresholds only; it does not validate CrSb physics."
        ),
    }


def load_summary_dir(summary_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for label in BASIS_LABELS:
        path = summary_dir / f"{label}.summary.json"
        if path.exists():
            out[label] = _load_summary(path)
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("summary_dir", type=Path)
    args = parser.parse_args()
    result = choose_next_basis_case(load_summary_dir(args.summary_dir))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parent
DEFAULT_TARGETS = ROOT / "manifests" / "qo_reference_targets_b000.json"


def _corr(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        raise ValueError("correlation requires equal vectors with >=2 entries")
    am = mean(a)
    bm = mean(b)
    da = sum((x - am) ** 2 for x in a)
    db = sum((y - bm) ** 2 for y in b)
    if da == 0.0 or db == 0.0:
        return float("nan")
    return sum((x-am)*(y-bm) for x,y in zip(a,b)) / math.sqrt(da*db)


def _pair_error(pred: list[float], obs: list[float]) -> tuple[list[float], float]:
    if len(pred) != 2 or len(obs) != 2:
        raise ValueError("exactly two frequencies required")
    direct = [abs(pred[0]-obs[0]), abs(pred[1]-obs[1])]
    swapped = [abs(pred[0]-obs[1]), abs(pred[1]-obs[0])]
    dmean = mean(direct)
    smean = mean(swapped)
    return (direct, dmean) if dmean <= smean else (swapped, smean)


def compare_qo(
    computed: dict,
    targets_path: Path = DEFAULT_TARGETS,
) -> dict:
    ref = json.loads(targets_path.read_text(encoding="utf-8"))
    target_by_alpha = {float(r["alpha_deg"]): r for r in ref["targets"]}
    rows = computed.get("angles", [])
    comp_by_alpha = {}
    duplicate_alphas = []
    for row in rows:
        alpha = float(row["alpha_deg"])
        if alpha in comp_by_alpha:
            duplicate_alphas.append(alpha)
        comp_by_alpha[alpha] = row

    missing = sorted(set(target_by_alpha) - set(comp_by_alpha))
    extras = sorted(set(comp_by_alpha) - set(target_by_alpha))
    invalid = []
    evaluated = []

    for alpha in sorted(target_by_alpha):
        if alpha not in comp_by_alpha:
            continue
        target = target_by_alpha[alpha]
        row = comp_by_alpha[alpha]
        freqs = row.get("dogbone_frequencies_kT")
        if (
            row.get("classification") != "dogbone"
            or not isinstance(freqs, list)
            or len(freqs) != 2
            or any(not isinstance(v, (int,float)) for v in freqs)
        ):
            invalid.append(alpha)
            continue

        obs = [float(v) for v in target["observed_frequencies_kT"]]
        pred = [float(v) for v in freqs]
        errors, pair_mae = _pair_error(pred, obs)
        pred_split = abs(pred[1]-pred[0])
        obs_split = abs(obs[1]-obs[0])
        evaluated.append({
            "alpha_deg": alpha,
            "node": bool(target["node"]),
            "predicted_frequencies_kT": pred,
            "observed_frequencies_kT": obs,
            "pair_abs_errors_kT": errors,
            "pair_mae_kT": pair_mae,
            "predicted_split_kT": pred_split,
            "observed_split_kT": obs_split,
        })

    accept = ref["engineering_acceptance"]
    coverage = len(evaluated)
    all_pair_mae = [r["pair_mae_kT"] for r in evaluated]
    overall_pair_mae = mean(all_pair_mae) if all_pair_mae else float("nan")

    node_rows = [r for r in evaluated if r["node"]]
    nodes_pass = (
        len(node_rows) == 2
        and all(r["predicted_split_kT"] <= float(accept["maximum_node_split_kT"]) for r in node_rows)
    )

    pred_splits = [r["predicted_split_kT"] for r in evaluated]
    obs_splits = [r["observed_split_kT"] for r in evaluated]
    split_corr = _corr(pred_splits, obs_splits) if coverage >= 2 else float("nan")
    corr_pass = math.isfinite(split_corr) and split_corr >= float(accept["minimum_split_correlation"])
    pair_pass = math.isfinite(overall_pair_mae) and overall_pair_mae <= float(accept["maximum_pair_mae_kT"])
    coverage_pass = (
        not missing
        and not extras
        and not invalid
        and not duplicate_alphas
        and coverage >= int(accept["minimum_angle_coverage"])
    )

    passed = coverage_pass and nodes_pass and corr_pass and pair_pass
    return {
        "program": ref["program"],
        "benchmark": ref["benchmark"],
        "lane": computed.get("lane"),
        "input_provenance": computed.get("provenance", {}),
        "coverage": coverage,
        "missing_alpha_deg": missing,
        "extra_alpha_deg": extras,
        "duplicate_alpha_deg": sorted(set(duplicate_alphas)),
        "invalid_alpha_deg": invalid,
        "rows": evaluated,
        "overall_pair_mae_kT": overall_pair_mae,
        "split_correlation": split_corr,
        "coverage_pass": coverage_pass,
        "nodes_pass": nodes_pass,
        "split_correlation_pass": corr_pass,
        "pair_mae_pass": pair_pass,
        "pass": passed,
        "decision": "QO_REFERENCE_MATCH" if passed else "HOLD",
        "claim_boundary": ref["claim_boundary"],
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("computed_json", type=Path)
    args = parser.parse_args()
    computed = json.loads(args.computed_json.read_text(encoding="utf-8"))
    print(json.dumps(compare_qo(computed), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

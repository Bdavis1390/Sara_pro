#!/usr/bin/env python3
"""Compute raw-search coverage and collision multiplicity over the active Glob union.

Permutation membership, raw-search observation density, and physical evidence are
kept as separate facts. Leading-zero five-character states remain strings.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "data" / "research"
ORIGINAL = RESEARCH / "glob_99073_registry.json"
P13524 = RESEARCH / "glob_99073_permutation_13524_registry.json"
P14523 = RESEARCH / "glob_99073_permutation_14523_registry.json"
RAW_GLOB = "glob_99073_raw_hit_reservoir_*.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def states_from_registry(path: Path) -> set[str]:
    data = load(path)
    states: set[str] = set()
    for entry in data["orbits"]:
        states.update(entry["orbit"])
    return states


def active_union() -> set[str]:
    return states_from_registry(ORIGINAL) | states_from_registry(P13524) | states_from_registry(P14523)


def raw_records() -> list[tuple[Path, dict]]:
    records: list[tuple[Path, dict]] = []
    for path in sorted(RESEARCH.glob(RAW_GLOB)):
        data = load(path)
        for record in data.get("records", []):
            records.append((path, record))
    return records


def build_report() -> dict:
    union = active_union()
    records = raw_records()
    observed: set[str] = set()
    namespace_counts: Counter[str] = Counter()
    weight_counts: Counter[str] = Counter()
    per_target: dict[str, dict] = defaultdict(
        lambda: {"records": 0, "namespaces": set(), "weights": set(), "files": [], "saw_no_hit": False, "saw_later_hit": False}
    )
    out_of_union: set[str] = set()

    for path, record in records:
        target = record["target"]
        if target not in union:
            out_of_union.add(target)
        observed.add(target)
        namespace_counts[record["raw_hit_type"]] += 1
        weight_counts[record["glob_weight"]] += 1
        row = per_target[target]
        row["records"] += 1
        row["namespaces"].add(record["raw_hit_type"])
        row["weights"].add(record["glob_weight"])
        row["files"].append(path.name)
        if record["glob_weight"] == "NO_HIT":
            row["saw_no_hit"] = True
        elif row["saw_no_hit"]:
            row["saw_later_hit"] = True

    covered = union & observed
    gaps = sorted(union - observed)
    normalized_per_target = {
        target: {
            "records": row["records"],
            "namespace_count": len(row["namespaces"]),
            "namespaces": sorted(row["namespaces"]),
            "weights": sorted(row["weights"]),
            "files": row["files"],
            "no_hit_revised_by_later_occurrence": row["saw_later_hit"],
        }
        for target, row in sorted(per_target.items())
        if target in union
    }

    record_depths = [normalized_per_target[state]["records"] for state in sorted(covered)]
    namespace_depths = [normalized_per_target[state]["namespace_count"] for state in sorted(covered)]
    dense_targets = sorted(
        (
            {"target": target, **row}
            for target, row in normalized_per_target.items()
        ),
        key=lambda item: (-item["records"], -item["namespace_count"], item["target"]),
    )
    revised_no_hits = sorted(
        target for target, row in normalized_per_target.items() if row["no_hit_revised_by_later_occurrence"]
    )
    sparse_targets = sorted(target for target, row in normalized_per_target.items() if row["records"] == 1)

    return {
        "schema_version": "ws-glob-raw-coverage-report-1.1",
        "union_unique_states": len(union),
        "covered_unique_states": len(covered),
        "coverage_fraction": round(len(covered) / len(union), 6),
        "remaining_gap_count": len(gaps),
        "remaining_states": gaps,
        "out_of_union_targets": sorted(out_of_union),
        "raw_record_count": len(records),
        "glob_weight_counts": dict(sorted(weight_counts.items())),
        "raw_namespace_counts": dict(sorted(namespace_counts.items())),
        "multiplicity": {
            "mean_records_per_covered_state": round(sum(record_depths) / len(record_depths), 6) if record_depths else 0.0,
            "median_records_per_covered_state": median(record_depths) if record_depths else 0,
            "max_records_for_single_state": max(record_depths) if record_depths else 0,
            "mean_namespaces_per_covered_state": round(sum(namespace_depths) / len(namespace_depths), 6) if namespace_depths else 0.0,
            "max_namespaces_for_single_state": max(namespace_depths) if namespace_depths else 0,
            "single_record_state_count": len(sparse_targets),
            "revised_no_hit_count": len(revised_no_hits),
        },
        "sparse_targets": sparse_targets,
        "revised_no_hit_targets": revised_no_hits,
        "densest_targets": dense_targets[:25],
        "per_target": normalized_per_target,
        "claims_boundary": "Coverage and collision multiplicity measure search-observation behavior only; neither implies physical evidence, causal relation, or statistical significance for the Glob hypothesis.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    report = build_report()
    text = json.dumps(report, indent=2, sort_keys=False)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    if args.require_complete and report["remaining_gap_count"]:
        print("RAW_COVERAGE_GAPS=" + ",".join(report["remaining_states"]))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

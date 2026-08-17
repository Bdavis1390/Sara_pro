#!/usr/bin/env python3
"""Compute raw-search coverage over the complete active Glob permutation union.

The analyzer treats permutation membership and raw-search observation as separate
facts. It does not score physical evidence. Leading-zero five-character states
remain strings throughout.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


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
    per_target: dict[str, dict] = defaultdict(lambda: {"records": 0, "namespaces": set(), "weights": set()})
    out_of_union: set[str] = set()

    for _, record in records:
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

    covered = union & observed
    gaps = sorted(union - observed)
    normalized_per_target = {
        target: {
            "records": row["records"],
            "namespaces": sorted(row["namespaces"]),
            "weights": sorted(row["weights"]),
        }
        for target, row in sorted(per_target.items())
        if target in union
    }

    return {
        "schema_version": "ws-glob-raw-coverage-report-1.0",
        "union_unique_states": len(union),
        "covered_unique_states": len(covered),
        "coverage_fraction": round(len(covered) / len(union), 6),
        "remaining_gap_count": len(gaps),
        "remaining_states": gaps,
        "out_of_union_targets": sorted(out_of_union),
        "raw_record_count": len(records),
        "glob_weight_counts": dict(sorted(weight_counts.items())),
        "raw_namespace_counts": dict(sorted(namespace_counts.items())),
        "per_target": normalized_per_target,
        "claims_boundary": "Coverage means a state has at least one explicit raw-search observation; it does not mean the state has physical evidence or statistical significance.",
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

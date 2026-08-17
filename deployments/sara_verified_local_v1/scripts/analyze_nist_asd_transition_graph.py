#!/usr/bin/env python3
"""Analyze a NIST ASD spectral-line export as a transition graph.

This utility is intentionally standard-library only.  It accepts the pipe-delimited
ASCII output recommended by NIST ASD help and also supports ordinary CSV/TSV
exports when lower/upper energy columns can be identified.

The analyzer never treats a numeric match as evidence by itself.  It produces
machine-readable topology facts for later PRIME SENTINEL statistical/claims gates:
endpoint degrees, Ritz wavenumber proximity to predeclared targets, and shared-node
motifs among those candidate matches.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


NUMBER_RE = re.compile(r"[-+]?\d[\d ]*(?:\.\d+)?(?:[Ee][-+]?\d+)?")
ENERGY_PAIR_RE = re.compile(
    r"\[?\s*([-+]?\d[\d ]*(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*\]?"
    r"\s*-\s*"
    r"\[?\s*([-+]?\d[\d ]*(?:\.\d+)?(?:[Ee][-+]?\d+)?)\s*\]?"
)


@dataclass(frozen=True)
class Transition:
    lower_cm1: float
    upper_cm1: float
    source_row: int

    @property
    def ritz_wavenumber_cm1(self) -> float:
        return self.upper_cm1 - self.lower_cm1


def clean_cell(value: str) -> str:
    value = value.strip().replace("\u2212", "-").replace("\xa0", " ")
    # NIST notes that CSV output may use spreadsheet formulas to preserve the
    # number of decimal places.  Unwrap common ="..." cells before parsing.
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    return value.strip().strip('"').strip()


def parse_number(value: str) -> float | None:
    value = clean_cell(value).strip("[]()")
    if not value:
        return None
    match = NUMBER_RE.search(value)
    if not match:
        return None
    token = match.group(0).replace(" ", "")
    try:
        parsed = float(token)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def parse_energy_pair(value: str) -> tuple[float, float] | None:
    value = clean_cell(value)
    match = ENERGY_PAIR_RE.search(value)
    if not match:
        return None
    lower = parse_number(match.group(1))
    upper = parse_number(match.group(2))
    if lower is None or upper is None or upper < lower:
        return None
    return lower, upper


def normalize_header(value: str) -> str:
    value = clean_cell(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _looks_like_pipe_ascii(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    return sum("|" in line for line in lines[:80]) >= 3


def _parse_pipe_ascii(text: str) -> list[Transition]:
    lines = text.splitlines()
    energy_index: int | None = None

    # NIST ASCII has a multi-row header.  The energy column is typically headed
    # "Ei Ek" on the first header row and contains values such as
    # "10592.485 - 50292.354" in data rows.
    for line in lines:
        if "|" not in line:
            continue
        cells = [normalize_header(cell) for cell in line.split("|")]
        for index, cell in enumerate(cells):
            compact = cell.replace(" ", "")
            if ("ei" in compact and "ek" in compact) or (
                "lower" in cell and "upper" in cell and "energy" in cell
            ):
                energy_index = index
                break
        if energy_index is not None:
            break

    transitions: list[Transition] = []
    for row_number, line in enumerate(lines, start=1):
        if "|" not in line or set(line.strip()) <= {"-", "|", "+", " "}:
            continue
        cells = line.split("|")
        candidates: Iterable[str]
        if energy_index is not None and energy_index < len(cells):
            candidates = (cells[energy_index],)
        else:
            # Conservative fallback: only accept a cell containing a parseable
            # lower-upper energy pair, never arbitrary numbers elsewhere.
            candidates = cells
        for cell in candidates:
            pair = parse_energy_pair(cell)
            if pair is None:
                continue
            lower, upper = pair
            transitions.append(Transition(lower, upper, row_number))
            break
    return transitions


def _read_delimited(text: str, delimiter: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def _find_energy_columns(header: Sequence[str]) -> tuple[int, int] | None:
    normalized = [normalize_header(cell) for cell in header]
    lower_candidates = {
        "ei",
        "e i",
        "lower energy",
        "lower level energy",
        "lower energy cm 1",
        "lower level energy cm 1",
    }
    upper_candidates = {
        "ek",
        "e k",
        "upper energy",
        "upper level energy",
        "upper energy cm 1",
        "upper level energy cm 1",
    }
    lower: int | None = None
    upper: int | None = None
    for index, value in enumerate(normalized):
        if value in lower_candidates or ("lower" in value and "energ" in value):
            lower = index
        if value in upper_candidates or ("upper" in value and "energ" in value):
            upper = index
    if lower is not None and upper is not None:
        return lower, upper
    return None


def _parse_delimited(text: str, delimiter: str) -> list[Transition]:
    rows = _read_delimited(text, delimiter)
    if not rows:
        return []

    header_index: int | None = None
    columns: tuple[int, int] | None = None
    for index, row in enumerate(rows[:30]):
        found = _find_energy_columns(row)
        if found is not None:
            header_index = index
            columns = found
            break

    if header_index is None or columns is None:
        # Some exports preserve Ei-Ek as one field rather than two columns.
        transitions: list[Transition] = []
        for row_number, row in enumerate(rows, start=1):
            for cell in row:
                pair = parse_energy_pair(cell)
                if pair is None:
                    continue
                transitions.append(Transition(pair[0], pair[1], row_number))
                break
        return transitions

    lower_index, upper_index = columns
    transitions = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if max(lower_index, upper_index) >= len(row):
            continue
        lower = parse_number(row[lower_index])
        upper = parse_number(row[upper_index])
        if lower is None or upper is None or upper < lower:
            continue
        transitions.append(Transition(lower, upper, row_number))
    return transitions


def parse_nist_export(text: str, input_format: str = "auto") -> list[Transition]:
    if input_format not in {"auto", "ascii", "csv", "tsv"}:
        raise ValueError(f"unsupported format: {input_format}")
    if input_format == "ascii" or (input_format == "auto" and _looks_like_pipe_ascii(text)):
        return _parse_pipe_ascii(text)
    if input_format == "tsv" or (input_format == "auto" and "\t" in text):
        return _parse_delimited(text, "\t")
    return _parse_delimited(text, ",")


def canonical_level(value: float, decimals: int = 9) -> float:
    return round(value, decimals)


def load_registry_targets(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    targets: set[int] = set()
    for record in payload.get("orbits", []):
        for state in record.get("orbit", []):
            if isinstance(state, str) and len(state) == 5 and state.isdigit():
                targets.add(int(state))
    return sorted(targets)


def analyze(
    transitions: Sequence[Transition],
    targets: Sequence[float],
    tolerance_cm1: float,
    query_levels: Sequence[float],
) -> dict:
    if tolerance_cm1 < 0:
        raise ValueError("tolerance must be non-negative")

    adjacency: dict[float, set[float]] = defaultdict(set)
    edge_rows: dict[tuple[float, float], list[int]] = defaultdict(list)
    for transition in transitions:
        lower = canonical_level(transition.lower_cm1)
        upper = canonical_level(transition.upper_cm1)
        adjacency[lower].add(upper)
        adjacency[upper].add(lower)
        edge_rows[(lower, upper)].append(transition.source_row)

    degrees = {level: len(neighbors) for level, neighbors in adjacency.items()}
    degree_histogram = Counter(degrees.values())

    level_queries = []
    for requested in query_levels:
        candidates = [
            (abs(level - requested), level, degrees[level]) for level in adjacency
        ]
        candidates.sort()
        nearest = candidates[0] if candidates else None
        level_queries.append(
            {
                "requested_cm-1": requested,
                "nearest_level_cm-1": nearest[1] if nearest else None,
                "abs_delta_cm-1": nearest[0] if nearest else None,
                "degree": nearest[2] if nearest else None,
            }
        )

    candidate_matches = []
    by_endpoint: dict[float, list[dict]] = defaultdict(list)
    for target in sorted(set(float(value) for value in targets)):
        matches = []
        for transition in transitions:
            ritz = transition.ritz_wavenumber_cm1
            delta = ritz - target
            if abs(delta) <= tolerance_cm1:
                match = {
                    "target_cm-1": target,
                    "ritz_wavenumber_cm-1": ritz,
                    "delta_cm-1": delta,
                    "lower_cm-1": transition.lower_cm1,
                    "upper_cm-1": transition.upper_cm1,
                    "source_row": transition.source_row,
                }
                matches.append(match)
                by_endpoint[canonical_level(transition.lower_cm1)].append(match)
                by_endpoint[canonical_level(transition.upper_cm1)].append(match)
        if matches:
            candidate_matches.append({"target_cm-1": target, "matches": matches})

    shared_endpoint_motifs = []
    for endpoint, matches in sorted(by_endpoint.items()):
        distinct_targets = sorted({match["target_cm-1"] for match in matches})
        if len(distinct_targets) < 2:
            continue
        shared_endpoint_motifs.append(
            {
                "endpoint_cm-1": endpoint,
                "degree": degrees.get(endpoint),
                "distinct_targets_cm-1": distinct_targets,
                "matches": matches,
            }
        )

    return {
        "schema_version": "ws-nist-asd-transition-graph-analysis-1.0",
        "claims_boundary": (
            "Numeric/topological matches are candidate facts only. Statistical significance "
            "requires a predeclared null model and multiple-testing correction."
        ),
        "input_summary": {
            "transition_rows_parsed": len(transitions),
            "unique_edges": len(edge_rows),
            "unique_levels": len(adjacency),
            "targets_tested": len(set(float(value) for value in targets)),
            "tolerance_cm-1": tolerance_cm1,
        },
        "degree_summary": {
            "minimum": min(degrees.values()) if degrees else None,
            "maximum": max(degrees.values()) if degrees else None,
            "mean": (sum(degrees.values()) / len(degrees)) if degrees else None,
            "histogram": {str(k): v for k, v in sorted(degree_histogram.items())},
        },
        "level_queries": level_queries,
        "candidate_target_matches": candidate_matches,
        "shared_endpoint_motifs": shared_endpoint_motifs,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="NIST ASD ASCII/CSV/TSV export")
    parser.add_argument(
        "--format",
        choices=("auto", "ascii", "csv", "tsv"),
        default="auto",
        help="input format (default: auto)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        help="Glob registry JSON; all five-digit orbit states become predeclared targets",
    )
    parser.add_argument(
        "--target",
        action="append",
        type=float,
        default=[],
        help="additional target wavenumber in cm^-1 (repeatable)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0,
        help="absolute Ritz-target tolerance in cm^-1 (default: 1.0)",
    )
    parser.add_argument(
        "--level",
        action="append",
        type=float,
        default=[],
        help="level whose nearest graph node/degree should be reported (repeatable)",
    )
    parser.add_argument("--output", type=Path, help="write JSON result to this file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = args.input.read_text(encoding="utf-8", errors="replace")
    transitions = parse_nist_export(text, args.format)
    if not transitions:
        raise SystemExit("No lower/upper energy pairs could be parsed from the export")

    targets = list(args.target)
    if args.registry:
        targets.extend(load_registry_targets(args.registry))

    result = analyze(
        transitions=transitions,
        targets=targets,
        tolerance_cm1=args.tolerance,
        query_levels=args.level,
    )
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert ExoAtom .states/.trans files into Worldshepherd transition-graph CSV.

ExoAtom stores atomic levels and transitions in the ExoMol format.  This adapter
joins transition state IDs to level energies and emits conservative lower/upper
energy rows that can be consumed by ``analyze_nist_asd_transition_graph.py``.

The adapter is an interoperability layer only.  A NIST-derived ExoAtom dataset
must not be counted as independent confirmation of the underlying NIST data.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, TextIO


@dataclass(frozen=True)
class ExoAtomTransition:
    upper_state_id: int
    lower_state_id: int
    lower_cm1: float
    upper_cm1: float
    reported_wavenumber_cm1: float | None
    source_row: int

    @property
    def energy_difference_cm1(self) -> float:
        return self.upper_cm1 - self.lower_cm1

    @property
    def reported_minus_energy_difference_cm1(self) -> float | None:
        if self.reported_wavenumber_cm1 is None:
            return None
        return self.reported_wavenumber_cm1 - self.energy_difference_cm1


def _finite_float(token: str) -> float | None:
    try:
        value = float(token)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def parse_states(text: str) -> dict[int, float]:
    """Return ``state_id -> energy_cm-1`` from an ExoAtom .states file.

    Only the first two fields are required (ID and energy); later quantum-number
    columns may contain spaces and are intentionally ignored by this adapter.
    """

    states: dict[int, float] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        try:
            state_id = int(parts[0])
        except ValueError:
            continue
        energy = _finite_float(parts[1])
        if energy is None:
            continue
        states[state_id] = energy
    return states


def parse_transitions(text: str, states: dict[int, float]) -> tuple[list[ExoAtomTransition], dict]:
    """Join an ExoAtom .trans file to states.

    ExoAtom transition files use the first two columns as upper-state ID ``i``
    and lower-state ID ``f``.  The fourth field, when present, is the reported
    wavenumber.  Rows whose state IDs cannot be resolved are skipped and counted.
    """

    transitions: list[ExoAtomTransition] = []
    unresolved = 0
    malformed = 0

    for row_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            malformed += 1
            continue
        try:
            upper_id = int(parts[0])
            lower_id = int(parts[1])
        except ValueError:
            malformed += 1
            continue
        if upper_id not in states or lower_id not in states:
            unresolved += 1
            continue

        energy_a = states[lower_id]
        energy_b = states[upper_id]
        lower_energy = min(energy_a, energy_b)
        upper_energy = max(energy_a, energy_b)
        reported = _finite_float(parts[3]) if len(parts) >= 4 else None

        transitions.append(
            ExoAtomTransition(
                upper_state_id=upper_id,
                lower_state_id=lower_id,
                lower_cm1=lower_energy,
                upper_cm1=upper_energy,
                reported_wavenumber_cm1=reported,
                source_row=row_number,
            )
        )

    summary = {
        "transition_rows_parsed": len(transitions),
        "transition_rows_unresolved_state_id": unresolved,
        "transition_rows_malformed": malformed,
        "states_resolved": len(states),
    }
    return transitions, summary


def write_csv(transitions: Sequence[ExoAtomTransition], handle: TextIO, spectrum: str) -> None:
    writer = csv.writer(handle)
    writer.writerow(
        [
            "Spectrum",
            "Lower Level Energy",
            "Upper Level Energy",
            "Reported Wavenumber",
            "Upper State ID",
            "Lower State ID",
            "Source Row",
            "Reported Minus Energy Difference",
        ]
    )
    for transition in transitions:
        writer.writerow(
            [
                spectrum,
                f"{transition.lower_cm1:.12g}",
                f"{transition.upper_cm1:.12g}",
                "" if transition.reported_wavenumber_cm1 is None else f"{transition.reported_wavenumber_cm1:.12g}",
                transition.upper_state_id,
                transition.lower_state_id,
                transition.source_row,
                ""
                if transition.reported_minus_energy_difference_cm1 is None
                else f"{transition.reported_minus_energy_difference_cm1:.12g}",
            ]
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", type=Path, required=True, help="ExoAtom .states file")
    parser.add_argument("--trans", type=Path, required=True, help="ExoAtom .trans file")
    parser.add_argument("--output", type=Path, required=True, help="Worldshepherd CSV output")
    parser.add_argument("--summary", type=Path, help="optional JSON ingestion summary")
    parser.add_argument("--spectrum", default="UNKNOWN", help="spectrum label, e.g. W II")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    states = parse_states(args.states.read_text(encoding="utf-8", errors="replace"))
    if not states:
        raise SystemExit("No ExoAtom state IDs/energies could be parsed")

    transitions, summary = parse_transitions(
        args.trans.read_text(encoding="utf-8", errors="replace"), states
    )
    if not transitions:
        raise SystemExit("No ExoAtom transitions could be joined to states")

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        write_csv(transitions, handle, args.spectrum)

    summary.update(
        {
            "schema_version": "ws-exoatom-transition-adapter-1.0",
            "spectrum": args.spectrum,
            "claims_boundary": (
                "This is an interoperability/cross-validation artifact. A NIST-derived "
                "ExoAtom dataset is not independent evidence from NIST ASD."
            ),
        }
    )
    if args.summary:
        args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

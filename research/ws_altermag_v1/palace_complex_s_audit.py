"""Read-only complex S-parameter diagnostic for Palace port-S.csv.

Never infers an observable error bound from the linear-solver residual.
Never labels low-power entries 'physical zero' without converged controls.
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
import cmath
import math
from pathlib import Path
import re


MAG_HEADER = re.compile(r"^\|(?P<channel>S\[\d+\]\[\d+\])\| \(dB\)$")
PHASE_HEADER = re.compile(r"^arg\((?P<channel>S\[\d+\]\[\d+\])\) \(deg\.\)$")


def _finite_real(value: str, *, allow_negative_inf: bool = False) -> float:
    try:
        x = float(value.strip())
    except ValueError as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc
    if math.isfinite(x) or (allow_negative_inf and x == float("-inf")):
        return x
    raise ValueError(f"disallowed nonfinite numeric value: {value!r}")


def parse_complex_s(path: Path) -> dict:
    raw = path.read_bytes()
    reader = csv.reader(raw.decode("utf-8", errors="replace").splitlines())
    header = next(reader, None)
    if header is None or not header:
        raise ValueError("Palace S file has no header")
    headings = [x.strip() for x in header]
    if headings[0] != "f (GHz)":
        raise ValueError(f"unexpected Palace frequency column {headings[0]!r}")
    if len(headings) != 5:
        raise ValueError(f"expected two magnitude/phase channel pairs, found {len(headings)} columns")

    channels = []
    for i in (1, 3):
        m = MAG_HEADER.fullmatch(headings[i])
        p = PHASE_HEADER.fullmatch(headings[i+1])
        if not m or not p or m.group("channel") != p.group("channel"):
            raise ValueError(f"invalid magnitude/phase pairing at column {i}")
        channels.append(m.group("channel"))
    if len(set(channels)) != len(channels):
        raise ValueError("duplicate S-parameter channel")

    records = []
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not x.strip() for x in row):
            continue
        if len(row) != len(headings):
            raise ValueError(f"row {lineno}: incorrect channel count")
        fghz = _finite_real(row[0])
        measured = {}
        for k, col in enumerate((1, 3)):
            db = _finite_real(row[col], allow_negative_inf=True)
            phase = _finite_real(row[col+1])
            # A -inf dB export is zero to the precision of the export, but it
            # does not prove a physical zero in an unconverged computation.
            if db == float("-inf"):
                z = complex(0, 0)
                phase_used = None
                amp = 0.0
            else:
                amp = 10 ** (db / 20)
                z = amp * cmath.exp(1j * math.radians(phase))
                phase_used = phase
                if not all(map(math.isfinite, (amp, z.real, z.imag))):
                    raise ValueError(f"nonfinite reconstructed S at line {lineno}")
            measured[channels[k]] = {
                "magnitude_db": db if math.isfinite(db) else None,
                "export_negative_inf_db": db == float("-inf"),
                "phase_deg": phase_used,
                "amplitude_linear": amp,
                "real": z.real,
                "imag": z.imag,
            }
        records.append({"frequency_GHz": fghz, "channels": measured})

    freqs = [r["frequency_GHz"] for r in records]
    if not records or any(b <= a for a, b in zip(freqs, freqs[1:])):
        raise ValueError("frequency grid must be nonempty and strictly increasing")

    grads = []
    for channel in channels:
        for a, b in zip(records, records[1:]):
            x = a["channels"][channel]
            y = b["channels"][channel]
            delta = complex(y["real"]-x["real"], y["imag"]-x["imag"])
            grads.append({
                "channel": channel,
                "frequency_start_GHz": a["frequency_GHz"],
                "frequency_end_GHz": b["frequency_GHz"],
                "complex_step_magnitude": abs(delta),
            })

    return {
        "source": str(path),
        "source_sha256": sha256(raw).hexdigest(),
        "channels": channels,
        "frequency_point_count": len(records),
        "rows": records,
        "complex_gradients": grads,
        "largest_complex_gradients": sorted(
            grads, key=lambda x:x["complex_step_magnitude"], reverse=True,
        )[:10],
        "claim_boundary": (
            "The complex values are reconstructed from the solver's magnitude/phase "
            "CSV export, not independent measurements. Exported -inf dB is zero to "
            "the export precision, not proof of a physical null. Adjacent changes "
            "and Krylov residuals do not establish errors on physical observables."
        ),
    }


def propose_spotchecks(s_report: dict, residual_report: dict, *, count: int = 8) -> dict:
    if count < 4:
        raise ValueError("at least four candidate frequencies required")
    rows = s_report["rows"]
    if len(rows) != residual_report["frequency_points_parsed"]:
        raise ValueError("S-parameter and residual profiles have different coverage")
    worst = residual_report["worst_twelve"]
    if not worst:
        raise ValueError("no recorded solver residuals")
    # The log frequency is rounded; use integer frequency-step IDs to join
    # it to the high-resolution CSV, never a floating equality join.
    selected: dict[int, set[str]] = {}

    def add(step: int, reason: str) -> None:
        if 1 <= step <= len(rows):
            selected.setdefault(step, set()).add(reason)

    add(1, "lower_band_edge_control")
    add((len(rows)+1)//2, "mid_band_control")
    add(len(rows), "upper_band_edge_control")
    for x in worst[:4]:
        add(int(x["step"]), "high_solver_residual")
    freq_to_step = {round(r["frequency_GHz"], 6): i for i, r in enumerate(rows, 1)}
    for grad in s_report["largest_complex_gradients"]:
        i = freq_to_step.get(round(grad["frequency_start_GHz"], 6))
        if i:
            add(i, f"complex_gradient_{grad['channel']}")
            add(i+1, f"complex_gradient_{grad['channel']}")
        if len(selected) >= count:
            break
    prioritized = sorted(
        selected,
        key=lambda step: (
            "high_solver_residual" not in selected[step],
            "lower_band_edge_control" not in selected[step],
            "mid_band_control" not in selected[step],
            "upper_band_edge_control" not in selected[step],
            step,
        )
    )[:count]
    return {
        "status": "PROPOSED_ONLY_NO_SOLVER_EXECUTION",
        "selected": [
            {
                "step": i,
                "frequency_GHz": rows[i-1]["frequency_GHz"],
                "reasons": sorted(selected[i]),
            }
            for i in sorted(prioritized)
        ],
        "policy": (
            "Select lower/mid/upper band controls, high residuals, and "
            "complex-response gradients without fitting to desired results. "
            "Prior to re-solving, document preconditioner changes, mesh and "
            "acceptance thresholds. Do not rerun during the Palace queue."
        ),
    }


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("port_s", type=Path)
    ap.add_argument("--residual-json", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    report = parse_complex_s(args.port_s)
    result = {
        "source": report["source"],
        "source_sha256": report["source_sha256"],
        "channels": report["channels"],
        "frequency_point_count": report["frequency_point_count"],
        "first_frequency": report["rows"][0],
        "last_frequency": report["rows"][-1],
        "largest_complex_gradients": report["largest_complex_gradients"],
        "claim_boundary": report["claim_boundary"],
    }
    if args.residual_json:
        residuals = json.loads(args.residual_json.read_text(encoding="utf-8"))
        result["spotcheck_plan"] = propose_spotchecks(report, residuals)
    data = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(args.output)
    print(data)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import zipfile

from .schema import digest
from .source_data_b000 import DEFAULT_MANIFEST, _load_manifest


def _hash(data: bytes) -> str:
    return sha256(data).hexdigest()


def _rows(raw: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(raw.decode("utf-8")), delimiter="\t"))


def _linear_interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo = 0
    hi = len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    frac = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] + frac * (ys[hi] - ys[lo])


def _parse_dft(raw: bytes) -> tuple[list[float], list[float], list[float], list[float]]:
    rows = _rows(raw)
    x1: list[float] = []
    y1: list[float] = []
    x2: list[float] = []
    y2: list[float] = []
    for row in rows[1:]:
        try:
            x1.append(float(row[0]))
            y1.append(float(row[1]))
            x2.append(float(row[2]))
            y2.append(float(row[3]))
        except (ValueError, IndexError):
            continue
    return x1, y1, x2, y2


def _parse_fft_series(raw: bytes) -> list[dict]:
    rows = _rows(raw)
    header = rows[0]
    out = []
    for i in range(0, len(header), 2):
        xs: list[float] = []
        ys: list[float] = []
        for row in rows[1:]:
            try:
                xs.append(float(row[i]))
                ys.append(float(row[i + 1]))
            except (ValueError, IndexError):
                continue
        match = re.search(r"=\s*([-+]?\d+(?:\.\d+)?)", header[i])
        alpha = float(match.group(1)) if match else None
        out.append({"alpha_deg": alpha, "header": header[i], "x": xs, "y": ys})
    return out


def _local_peaks(
    xs: list[float],
    ys: list[float],
    lo: float,
    hi: float,
    min_amp: float,
) -> list[tuple[float, float]]:
    baseline = ys[0]
    peaks = []
    for j in range(1, len(xs) - 1):
        amp = ys[j] - baseline
        if (
            lo <= xs[j] <= hi
            and amp >= min_amp
            and ys[j] > ys[j - 1]
            and ys[j] >= ys[j + 1]
        ):
            peaks.append((xs[j], amp))
    return peaks


def _nearest_peak(predicted: float, peaks: list[tuple[float, float]]) -> tuple[float, float, float]:
    frequency, amplitude = min(peaks, key=lambda p: abs(p[0] - predicted))
    return frequency, amplitude, abs(frequency - predicted)


def _corr(a: list[float], b: list[float]) -> float:
    am = sum(a) / len(a)
    bm = sum(b) / len(b)
    num = sum((x - am) * (y - bm) for x, y in zip(a, b))
    da = sum((x - am) ** 2 for x in a)
    db = sum((y - bm) ** 2 for y in b)
    return num / math.sqrt(da * db)


def analyze_angular(zip_path: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = _load_manifest(manifest_path)
    settings = manifest["analysis_angular"]
    archive = zip_path.read_bytes()

    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        dft_raw = zf.read(settings["dft_member"])
        fft_raw = zf.read(settings["fft_member"])

    hashes_ok = (
        _hash(dft_raw) == settings["dft_member_sha256"]
        and _hash(fft_raw) == settings["fft_member_sha256"]
    )

    x1, y1, x2, y2 = _parse_dft(dft_raw)
    lo, hi = map(float, settings["frequency_window_kT"])
    min_amp = float(settings["minimum_peak_amplitude_above_trace_baseline"])
    node_alphas = {float(v) for v in settings["declared_node_alpha_deg"]}

    rows = []
    for series in _parse_fft_series(fft_raw):
        alpha = float(series["alpha_deg"])
        dft_x = alpha + 90.0
        pred1 = _linear_interp(dft_x, x1, y1)
        pred2 = _linear_interp(dft_x, x2, y2)
        pred_split = abs(pred1 - pred2)

        peaks = _local_peaks(series["x"], series["y"], lo, hi, min_amp)
        obs1 = _nearest_peak(pred1, peaks)
        obs2 = _nearest_peak(pred2, peaks)
        obs_split = abs(obs1[0] - obs2[0])

        node = alpha in node_alphas
        off_node = pred_split >= float(settings["off_node_predicted_split_min_kT"])
        branch_match_ok = (
            obs1[2] <= float(settings["max_branch_match_error_kT"])
            and obs2[2] <= float(settings["max_branch_match_error_kT"])
        )

        rows.append(
            {
                "alpha_deg": alpha,
                "exported_dft_x_deg": dft_x,
                "predicted_frequencies_kT": [pred1, pred2],
                "predicted_split_kT": pred_split,
                "observed_frequencies_kT": [obs1[0], obs2[0]],
                "observed_split_kT": obs_split,
                "branch_match_errors_kT": [obs1[2], obs2[2]],
                "node": node,
                "off_node": off_node,
                "branch_match_ok": branch_match_ok,
            }
        )

    node_rows = [r for r in rows if r["node"]]
    off_rows = [r for r in rows if r["off_node"] and not r["node"] and r["branch_match_ok"]]

    nodes_pass = (
        len(node_rows) == len(node_alphas)
        and all(
            r["predicted_split_kT"] <= float(settings["predicted_node_split_max_kT"])
            and r["observed_split_kT"] <= float(settings["observed_node_split_max_kT"])
            and r["branch_match_ok"]
            for r in node_rows
        )
    )

    off_pass = (
        len(off_rows) >= int(settings["minimum_off_node_matches"])
        and all(
            r["observed_split_kT"] >= float(settings["off_node_observed_split_min_kT"])
            for r in off_rows
        )
    )

    predicted = [r["predicted_split_kT"] for r in off_rows]
    observed = [r["observed_split_kT"] for r in off_rows]
    correlation = _corr(predicted, observed) if len(off_rows) >= 2 else float("nan")
    corr_pass = correlation >= float(settings["minimum_split_correlation"])

    overall = hashes_ok and nodes_pass and off_pass and corr_pass
    record = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-ANGULAR",
        "archive_sha256": _hash(archive),
        "dft_member_sha256_actual": _hash(dft_raw),
        "fft_member_sha256_actual": _hash(fft_raw),
        "settings": settings,
        "rows": rows,
        "node_rows": node_rows,
        "off_node_match_count": len(off_rows),
        "split_correlation": correlation,
        "hashes_ok": hashes_ok,
        "nodes_pass": nodes_pass,
        "off_nodes_pass": off_pass,
        "correlation_pass": corr_pass,
        "pass": overall,
        "claim_status": ["PROVEN INTERNALLY", "SUPPORTED BY LITERATURE"],
        "claim_boundary": (
            "This is a theory-guided re-analysis of published Fig. 3 source data. "
            "The DFT profile is used to associate experimental FFT peaks with the two dogbone branches, "
            "so this is not a theory-independent experimental replication."
        ),
    }
    record["evidence_digest"] = digest(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze_angular(args.zip)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import re
import urllib.request
import zipfile

from .schema import digest


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "crsb_dataset_b000.json"


def _load_manifest(path: Path = DEFAULT_MANIFEST) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def fetch_dataset(destination: Path, manifest_path: Path = DEFAULT_MANIFEST) -> Path:
    manifest = _load_manifest(manifest_path)
    url = manifest["dataset"]["download_url"]
    with urllib.request.urlopen(url, timeout=90) as response:
        data = response.read()
    actual = _sha256_bytes(data)
    expected = manifest["dataset"]["archive_sha256"]
    if actual != expected:
        raise ValueError(f"archive SHA256 mismatch: expected {expected}, got {actual}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination


def _parse_pairs(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    header = rows[0]
    series = []
    for i in range(0, len(header), 2):
        xs: list[float] = []
        ys: list[float] = []
        for row in rows[1:]:
            try:
                xs.append(float(row[i]))
                ys.append(float(row[i + 1]))
            except (ValueError, IndexError):
                continue
        m = re.search(r"=\s*([-+]?\d+(?:\.\d+)?)", header[i])
        label_value = float(m.group(1)) if m else None
        series.append({"header": header[i], "label_value": label_value, "x": xs, "y": ys})
    return series


def _two_dominant_peaks(
    xs: list[float],
    ys: list[float],
    lo: float,
    hi: float,
    min_sep: float,
) -> list[dict[str, float]]:
    local = []
    for j in range(1, len(xs) - 1):
        if lo <= xs[j] <= hi and ys[j] > ys[j - 1] and ys[j] >= ys[j + 1]:
            local.append((ys[j], xs[j]))
    local.sort(reverse=True)

    selected: list[tuple[float, float]] = []
    for amplitude, frequency in local:
        if all(abs(frequency - f0) >= min_sep for _, f0 in selected):
            selected.append((amplitude, frequency))
        if len(selected) == 2:
            break

    if len(selected) != 2:
        return []

    return [
        {"frequency_kT": float(f), "amplitude": float(a)}
        for a, f in sorted(selected, key=lambda item: item[1])
    ]


def analyze_source_zip(zip_path: Path, manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = _load_manifest(manifest_path)
    archive = zip_path.read_bytes()
    archive_sha = _sha256_bytes(archive)
    expected_archive_sha = manifest["dataset"]["archive_sha256"]

    member_name = manifest["analysis"]["member"]
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        raw = zf.read(member_name)

    member_sha = _sha256_bytes(raw)
    expected_member_sha = manifest["analysis"]["member_sha256"]
    settings = manifest["analysis"]
    lo, hi = map(float, settings["frequency_window_kT"])
    min_sep = float(settings["minimum_peak_separation_kT"])

    spectra = []
    for item in _parse_pairs(raw):
        peaks = _two_dominant_peaks(item["x"], item["y"], lo, hi, min_sep)
        spectra.append(
            {
                "source_header": item["header"],
                "series_label_value": item["label_value"],
                "peaks": peaks,
                "split_kT": (
                    abs(peaks[1]["frequency_kT"] - peaks[0]["frequency_kT"])
                    if len(peaks) == 2
                    else None
                ),
            }
        )

    first = spectra[0]
    expected_first = settings["expected_first_spectrum"]
    f1 = first["peaks"][0]["frequency_kT"] if len(first["peaks"]) == 2 else float("nan")
    f2 = first["peaks"][1]["frequency_kT"] if len(first["peaks"]) == 2 else float("nan")
    split = first["split_kT"] if first["split_kT"] is not None else float("nan")

    def inside(value: float, bounds: list[float]) -> bool:
        return float(bounds[0]) <= value <= float(bounds[1])

    all_splits = [float(s["split_kT"]) for s in spectra if s["split_kT"] is not None]
    overall = (
        archive_sha == expected_archive_sha
        and member_sha == expected_member_sha
        and len(all_splits) == len(spectra)
        and inside(f1, expected_first["f1_kT_range"])
        and inside(f2, expected_first["f2_kT_range"])
        and inside(split, expected_first["split_kT_range"])
        and all(inside(v, settings["all_spectra_split_kT_range"]) for v in all_splits)
    )

    record = {
        "program": "WS-ALTERMAG",
        "benchmark": "B000-DATA",
        "source": manifest["dataset"],
        "archive_sha256_actual": archive_sha,
        "member": member_name,
        "member_sha256_actual": member_sha,
        "analysis_settings": settings,
        "spectra": spectra,
        "mean_split_kT": sum(all_splits) / len(all_splits),
        "min_split_kT": min(all_splits),
        "max_split_kT": max(all_splits),
        "pass": overall,
        "claim_status": ["PROVEN INTERNALLY", "SUPPORTED BY LITERATURE"],
        "claim_boundary": (
            "The bounded claim is that this code reproducibly extracts the published two-peak "
            "frequency splitting from the pinned official source-data archive. It does not constitute "
            "an independent physical replication of the CrSb experiment."
        ),
    }
    record["evidence_digest"] = digest(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--fetch-to", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    zip_path = args.zip
    if args.fetch_to is not None:
        zip_path = fetch_dataset(args.fetch_to)
    if zip_path is None:
        raise SystemExit("provide --zip PATH or --fetch-to PATH")

    result = analyze_source_zip(zip_path)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()

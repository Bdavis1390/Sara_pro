#!/usr/bin/env python3
"""Fetch and validate two pinned FAIR-MAST Zarr chunks without persisting values.

This script is an offline evidence-generation utility, not a control component.
It fetches only the `time/0` and `plasma_current/0` chunks identified by the
metadata gate, decodes them with their declared Zarr compressor/dtype, computes
integrity and quality statistics, and emits hashes/statistics only.  Raw signal
values are never written to the output report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import numpy as np
from numcodecs import get_codec


ALLOWED_HOST = "s3.echo.stfc.ac.uk"
MAX_CHUNK_BYTES = 10_000_000


def fetch_bytes(url: str, *, max_bytes: int = MAX_CHUNK_BYTES, timeout_s: float = 30.0) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise ValueError("data_probe_url_not_allowlisted")
    request = Request(url, method="GET", headers={"User-Agent": "Worldshepherd-FAIR-MAST-data-probe/0.1"})
    with urlopen(request, timeout=timeout_s) as response:  # nosec B310: host allowlisted above
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"chunk_http_status:{status}:{url}")
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"chunk_exceeds_bound:{url}")
    return raw


def fetch_json(url: str) -> Dict[str, Any]:
    raw = fetch_bytes(url, max_bytes=2_000_000)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("metadata_not_object")
    return payload


def decode_single_chunk(base: str, signal: str) -> Tuple[np.ndarray, Dict[str, Any]]:
    zarray = fetch_json(f"{base}/{signal}/.zarray")
    shape = zarray.get("shape")
    chunks = zarray.get("chunks")
    if not isinstance(shape, list) or len(shape) != 1:
        raise ValueError(f"unsupported_rank:{signal}")
    if not isinstance(chunks, list) or chunks != shape:
        raise ValueError(f"expected_single_full_length_chunk:{signal}")

    chunk_url = f"{base}/{signal}/0"
    compressed = fetch_bytes(chunk_url)
    compressed_sha = hashlib.sha256(compressed).hexdigest()

    compressor = zarray.get("compressor")
    if compressor is None:
        decoded = compressed
    else:
        decoded = get_codec(compressor).decode(compressed)
        if isinstance(decoded, np.ndarray):
            decoded = decoded.tobytes(order="C")
        else:
            decoded = bytes(decoded)

    dtype = np.dtype(str(zarray["dtype"]))
    values = np.frombuffer(decoded, dtype=dtype)
    expected_count = int(shape[0])
    if values.size != expected_count:
        raise ValueError(f"decoded_length_mismatch:{signal}:{values.size}:{expected_count}")

    decoded_sha = hashlib.sha256(values.tobytes(order="C")).hexdigest()
    evidence = {
        "chunk_url": chunk_url,
        "compressed_bytes": len(compressed),
        "compressed_sha256": compressed_sha,
        "decoded_bytes": int(values.nbytes),
        "decoded_sha256": decoded_sha,
        "count": int(values.size),
        "dtype": str(values.dtype),
    }
    return values, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/fair_mast/shot_30420_amc_manifest.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    endpoint = str(manifest["s3_endpoint"]).rstrip("/")
    zarr_uri = str(manifest["zarr_uri"])
    parsed = urlparse(zarr_uri)
    if parsed.scheme != "s3" or parsed.netloc != "mast":
        raise ValueError("manifest_zarr_uri_not_allowlisted")
    base = f"{endpoint}/{parsed.netloc}{parsed.path.rstrip('/')}"

    time_values, time_evidence = decode_single_chunk(base, "time")
    current_values, current_evidence = decode_single_chunk(base, "plasma_current")
    if time_values.shape != current_values.shape:
        raise ValueError("time_current_shape_mismatch")

    time_finite = np.isfinite(time_values)
    current_finite = np.isfinite(current_values)
    paired_finite = time_finite & current_finite
    finite_time_values = time_values[time_finite].astype(np.float64)
    finite_current_values = current_values[current_finite].astype(np.float64)
    if finite_time_values.size < 2:
        raise ValueError("insufficient_finite_time_values")

    time_diffs = np.diff(finite_time_values)
    monotonic_non_decreasing = bool(np.all(time_diffs >= 0))
    strictly_increasing = bool(np.all(time_diffs > 0))

    analysis_mask = paired_finite & (time_values >= 0.0) & (time_values <= 0.35)
    analysis_indices = np.nonzero(analysis_mask)[0]
    if analysis_indices.size:
        paired_bytes = (
            time_values[analysis_mask].astype("<f4", copy=False).tobytes(order="C")
            + current_values[analysis_mask].astype("<f4", copy=False).tobytes(order="C")
        )
        window_sha = hashlib.sha256(paired_bytes).hexdigest()
        first_index = int(analysis_indices[0])
        last_index = int(analysis_indices[-1])
    else:
        window_sha = None
        first_index = None
        last_index = None

    report = {
        "schema": "worldshepherd.fair_mast.data_probe.v1",
        "archive": "FAIR-MAST",
        "shot_id": int(manifest["shot_id"]),
        "data_level": str(manifest["data_level"]),
        "diagnostic_group": str(manifest["diagnostic_group"]),
        "zarr_uri": zarr_uri,
        "raw_values_persisted": False,
        "machine_control_authority": False,
        "uncertainty_metadata_available": False,
        "control_evidence_eligible": False,
        "time": {
            **time_evidence,
            "units": "s",
            "finite_count": int(time_finite.sum()),
            "finite_fraction": float(time_finite.mean()),
            "min": float(finite_time_values.min()),
            "max": float(finite_time_values.max()),
            "monotonic_non_decreasing": monotonic_non_decreasing,
            "strictly_increasing": strictly_increasing,
            "dt_min": float(time_diffs.min()),
            "dt_median": float(np.median(time_diffs)),
            "dt_max": float(time_diffs.max()),
        },
        "plasma_current": {
            **current_evidence,
            "units": "kA",
            "upstream_quality": "Not Checked",
            "finite_count": int(current_finite.sum()),
            "finite_fraction": float(current_finite.mean()),
            "min": float(finite_current_values.min()),
            "max": float(finite_current_values.max()),
            "mean": float(finite_current_values.mean()),
            "std": float(finite_current_values.std()),
        },
        "paired_window_0_to_0_35_s": {
            "finite_sample_count": int(analysis_mask.sum()),
            "first_index": first_index,
            "last_index": last_index,
            "paired_values_sha256": window_sha,
            "raw_values_in_report": False,
        },
        "control_blockers": [
            "Upstream signal quality is Not Checked.",
            "No uncertainty metadata is available in the probed signal attributes.",
            "This probe validates archive data integrity/statistics only; it is not a plasma-state estimator."
        ]
    }

    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    report["report_sha256"] = hashlib.sha256(canonical).hexdigest()
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

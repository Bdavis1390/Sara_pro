"""Bounded read-only metadata probe for a pinned FAIR-MAST Zarr source.

The probe intentionally reads only Zarr metadata objects (.zgroup, .zattrs,
.zarray).  It never fetches array chunk payloads and has no control-system
transport.  The result is a provenance report containing URL, size, SHA-256,
and parsed metadata for the exact objects inspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen


JsonFetcher = Callable[[str], Tuple[Dict[str, Any], bytes]]


def zarr_http_base(endpoint: str, zarr_uri: str) -> str:
    endpoint_parsed = urlparse(endpoint)
    if endpoint_parsed.scheme != "https":
        raise ValueError("endpoint_must_use_https")
    if endpoint_parsed.hostname != "s3.echo.stfc.ac.uk":
        raise ValueError("endpoint_host_not_allowlisted")

    zarr_parsed = urlparse(zarr_uri)
    if zarr_parsed.scheme != "s3" or not zarr_parsed.netloc:
        raise ValueError("zarr_uri_must_be_s3")
    if zarr_parsed.netloc != "mast":
        raise ValueError("zarr_bucket_not_allowlisted")

    return f"{endpoint.rstrip('/')}/{zarr_parsed.netloc}{zarr_parsed.path.rstrip('/')}"


def fetch_json_object(url: str, *, timeout_s: float = 20.0, max_bytes: int = 2_000_000) -> Tuple[Dict[str, Any], bytes]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "s3.echo.stfc.ac.uk":
        raise ValueError("probe_url_not_allowlisted")
    request = Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "Worldshepherd-FAIR-MAST-metadata-probe/0.1"},
    )
    with urlopen(request, timeout=timeout_s) as response:  # nosec B310: host is allowlisted above
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"metadata_object_http_status:{status}:{url}")
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError(f"metadata_object_too_large:{url}")
    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError(f"metadata_object_not_json_object:{url}")
    return decoded, raw


def _evidence(url: str, payload: Mapping[str, Any], raw: bytes) -> Dict[str, Any]:
    return {
        "url": url,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "metadata": dict(payload),
    }


def probe_source_manifest(manifest: Mapping[str, Any], *, fetcher: JsonFetcher = fetch_json_object) -> Dict[str, Any]:
    if manifest.get("status") != "SOURCE_MANIFEST_ONLY_NO_ARCHIVED_VALUES_EMBEDDED":
        raise ValueError("manifest_status_not_source_only")
    endpoint = str(manifest["s3_endpoint"])
    zarr_uri = str(manifest["zarr_uri"])
    signals = manifest.get("signals")
    if not isinstance(signals, list) or not signals:
        raise ValueError("manifest_signals_missing")

    base = zarr_http_base(endpoint, zarr_uri)
    objects: Dict[str, Any] = {}

    for relative in (".zgroup", ".zattrs"):
        url = f"{base}/{relative}"
        payload, raw = fetcher(url)
        objects[relative] = _evidence(url, payload, raw)

    signal_objects: Dict[str, Any] = {}
    for signal in signals:
        signal_name = str(signal).strip()
        if not signal_name or "/" in signal_name:
            raise ValueError(f"invalid_manifest_signal:{signal_name}")
        signal_evidence: Dict[str, Any] = {}
        for relative in (".zarray", ".zattrs"):
            url = f"{base}/{signal_name}/{relative}"
            payload, raw = fetcher(url)
            signal_evidence[relative] = _evidence(url, payload, raw)
        signal_objects[signal_name] = signal_evidence

    canonical = {
        "schema": "worldshepherd.fair_mast.metadata_probe.v1",
        "archive": manifest.get("archive"),
        "shot_id": manifest.get("shot_id"),
        "data_level": manifest.get("data_level"),
        "diagnostic_group": manifest.get("diagnostic_group"),
        "zarr_uri": zarr_uri,
        "http_base": base,
        "objects": objects,
        "signals": signal_objects,
        "array_chunks_fetched": False,
        "machine_control_authority": False,
    }
    report_bytes = json.dumps(canonical, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    canonical["report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    return canonical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="data/fair_mast/shot_30420_amc_manifest.json",
    )
    parser.add_argument("--output")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = probe_source_manifest(manifest)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

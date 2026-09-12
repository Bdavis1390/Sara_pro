import json

import pytest

from worldshepherd_sara.fair_mast_probe import probe_source_manifest, zarr_http_base


def manifest():
    return {
        "status": "SOURCE_MANIFEST_ONLY_NO_ARCHIVED_VALUES_EMBEDDED",
        "archive": "FAIR-MAST",
        "shot_id": 30420,
        "data_level": "level1",
        "diagnostic_group": "amc",
        "signals": ["time", "plasma_current"],
        "zarr_uri": "s3://mast/level1/shots/30420.zarr/amc",
        "s3_endpoint": "https://s3.echo.stfc.ac.uk",
    }


def fake_fetcher(url: str):
    if url.endswith("/.zgroup"):
        payload = {"zarr_format": 2}
    elif url.endswith("/time/.zarray"):
        payload = {"shape": [3], "chunks": [3], "dtype": "<f8"}
    elif url.endswith("/plasma_current/.zarray"):
        payload = {"shape": [3], "chunks": [3], "dtype": "<f4"}
    elif url.endswith("/time/.zattrs"):
        payload = {"units": "s"}
    elif url.endswith("/plasma_current/.zattrs"):
        payload = {"units": "kA"}
    elif url.endswith("/.zattrs"):
        payload = {"shot_id": 30420}
    else:
        raise AssertionError(f"unexpected URL {url}")
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return payload, raw


def test_http_base_is_exact_allowlisted_archive_path():
    assert zarr_http_base(
        "https://s3.echo.stfc.ac.uk",
        "s3://mast/level1/shots/30420.zarr/amc",
    ) == "https://s3.echo.stfc.ac.uk/mast/level1/shots/30420.zarr/amc"

    with pytest.raises(ValueError, match="endpoint_host_not_allowlisted"):
        zarr_http_base("https://example.com", "s3://mast/level1/shots/30420.zarr/amc")

    with pytest.raises(ValueError, match="zarr_bucket_not_allowlisted"):
        zarr_http_base("https://s3.echo.stfc.ac.uk", "s3://other/level1/shots/30420.zarr/amc")


def test_probe_reads_only_metadata_objects_and_is_hash_stable():
    first = probe_source_manifest(manifest(), fetcher=fake_fetcher)
    second = probe_source_manifest(manifest(), fetcher=fake_fetcher)

    assert first["array_chunks_fetched"] is False
    assert first["machine_control_authority"] is False
    assert set(first["signals"]) == {"time", "plasma_current"}
    assert first["signals"]["time"][".zattrs"]["metadata"]["units"] == "s"
    assert first["signals"]["plasma_current"][".zattrs"]["metadata"]["units"] == "kA"
    assert first["report_sha256"] == second["report_sha256"]

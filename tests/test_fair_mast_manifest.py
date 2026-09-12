import json
from pathlib import Path

from worldshepherd_sara.fair_mast_adapter import FairMastSource


MANIFEST = Path("data/fair_mast/shot_30420_amc_manifest.json")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_is_source_only_and_does_not_claim_embedded_archive_values():
    manifest = load_manifest()
    assert manifest["status"] == "SOURCE_MANIFEST_ONLY_NO_ARCHIVED_VALUES_EMBEDDED"
    assert manifest["claims_boundary"]["real_archive_values_in_repository"] is False
    assert manifest["claims_boundary"]["live_machine_data"] is False
    assert manifest["claims_boundary"]["machine_control_authority"] is False


def test_manifest_matches_adapter_generated_archive_identity():
    manifest = load_manifest()
    source = FairMastSource(
        shot_id=manifest["shot_id"],
        diagnostic_group=manifest["diagnostic_group"],
        signal="plasma_current",
        level=manifest["data_level"],
    )
    assert source.zarr_uri == manifest["zarr_uri"]
    assert manifest["s3_endpoint"] == "https://s3.echo.stfc.ac.uk"
    assert "time" in manifest["signals"]
    assert source.signal in manifest["signals"]


def test_manifest_contains_upstream_evidence_references():
    manifest = load_manifest()
    refs = {entry["reference"] for entry in manifest["source_evidence"]}
    assert "https://github.com/ukaea/fair-mast" in refs
    assert "https://github.com/ukaea/fair-mast/issues/107" in refs

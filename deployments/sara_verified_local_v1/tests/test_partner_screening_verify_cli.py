import json

import pytest

from worldshepherd_sara.geo_provenance import build_geo_prov_bundle
from worldshepherd_sara.partner_screening_cli import export_partner_screening_batch, export_partner_screening_package
from worldshepherd_sara.partner_screening_verify_cli import (
    main as verify_main,
    verify_partner_screening_batch,
    verify_partner_screening_package,
)


def _geo_bundle():
    return build_geo_prov_bundle(
        software_commit="test-manifest-verifier",
        executed_utc="2026-09-01T16:40:00Z",
        operator="pytest",
    )


def _write_bundle(path, bundle):
    path.write_text(json.dumps(bundle, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def test_verify_partner_screening_package_accepts_exported_package(tmp_path):
    out = tmp_path / "package"
    manifest = export_partner_screening_package(_geo_bundle(), out, partner="BAE_SYSTEMS")

    report = verify_partner_screening_package(out)

    assert report["schema"] == "WS-PARTNER-SCREENING-VERIFY-V1"
    assert report["status"] == "PASS"
    assert report["verification_scope"] == "partner_screening_package"
    assert report["partner_id"] == "BAE_SYSTEMS"
    assert report["manifest_bootstrap_digest"] == manifest["artifact_digests"]["manifest.json"]
    assert "manifest.json" in report["checked_files"]
    assert "qualification-summary.json" in report["checked_files"]
    assert "claims-boundary.md" in report["checked_files"]


def test_verify_partner_screening_package_rejects_tampered_file(tmp_path):
    out = tmp_path / "package"
    export_partner_screening_package(_geo_bundle(), out, partner="BAE_SYSTEMS")
    (out / "claims-boundary.md").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        verify_partner_screening_package(out)


def test_verify_partner_screening_batch_accepts_exported_batch(tmp_path):
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    _write_bundle(bundle_dir / "geo_prov_qualification_bundle.json", _geo_bundle())
    out = tmp_path / "batch-screening"

    manifest = export_partner_screening_batch(bundle_dir, out, partners=("BAE_SYSTEMS", "GENERIC_PRIME"))
    report = verify_partner_screening_batch(out)

    assert report["schema"] == "WS-PARTNER-SCREENING-VERIFY-V1"
    assert report["status"] == "PASS"
    assert report["verification_scope"] == "partner_screening_batch"
    assert set(report["partners"]) == {"BAE_SYSTEMS", "GENERIC_PRIME"}
    assert report["source_bundle_count"] == 1
    assert report["package_count"] == 2
    assert report["verified_package_count"] == 2
    assert report["batch_digest"] == manifest["batch_digest"]


def test_verify_partner_screening_batch_rejects_tampered_batch_manifest(tmp_path):
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    _write_bundle(bundle_dir / "geo_prov_qualification_bundle.json", _geo_bundle())
    out = tmp_path / "batch-screening"
    export_partner_screening_batch(bundle_dir, out, partners=("BAE_SYSTEMS", "GENERIC_PRIME"))

    manifest_path = out / "batch-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["package_count"] = 999
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="package_count"):
        verify_partner_screening_batch(out)


def test_verify_cli_returns_nonzero_on_tamper(tmp_path, capsys):
    out = tmp_path / "package"
    export_partner_screening_package(_geo_bundle(), out, partner="BAE_SYSTEMS")
    (out / "claims-boundary.md").write_text("tampered\n", encoding="utf-8")

    rc = verify_main(["--package", str(out)])

    captured = capsys.readouterr()
    assert rc == 1
    assert '"status": "FAIL"' in captured.err
    assert "digest mismatch" in captured.err

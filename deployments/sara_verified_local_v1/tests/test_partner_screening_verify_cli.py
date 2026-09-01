import json
import shutil

import pytest

from worldshepherd_sara.geo_provenance import build_geo_prov_bundle
from worldshepherd_sara.partner_screening_cli import export_partner_screening_batch, export_partner_screening_package
from worldshepherd_sara.partner_screening_verify_cli import (
    main as verify_main,
    verify_partner_screening_batch,
    verify_partner_screening_package,
)
from worldshepherd_sara.qualification import canonical_digest


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


def test_verify_partner_screening_package_requires_manifest_self_digest(tmp_path):
    out = tmp_path / "package"
    export_partner_screening_package(_geo_bundle(), out, partner="BAE_SYSTEMS")
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_digests"].pop("manifest.json")
    _write_bundle(manifest_path, manifest)

    with pytest.raises(ValueError, match="artifact digest missing.*manifest.json"):
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


def test_verify_partner_screening_batch_rejects_duplicate_cartesian_identity(tmp_path):
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    _write_bundle(bundle_dir / "geo_prov_qualification_bundle.json", _geo_bundle())
    out = tmp_path / "batch-screening"
    export_partner_screening_batch(bundle_dir, out, partners=("BAE_SYSTEMS", "GENERIC_PRIME"))

    manifest_path = out / "batch-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["exports"][1] = dict(manifest["exports"][0])
    manifest.pop("batch_digest")
    manifest["batch_digest"] = canonical_digest(manifest)
    _write_bundle(manifest_path, manifest)

    with pytest.raises(ValueError, match="duplicate partner/lane identities"):
        verify_partner_screening_batch(out)


def test_verify_partner_screening_batch_never_resolves_package_outside_batch_root(tmp_path):
    bundle_dir = tmp_path / "bundles"
    bundle_dir.mkdir()
    _write_bundle(bundle_dir / "geo_prov_qualification_bundle.json", _geo_bundle())
    original = tmp_path / "original-batch"
    export_partner_screening_batch(bundle_dir, original, partners=("BAE_SYSTEMS",))

    copied = tmp_path / "copied-batch"
    shutil.copytree(original, copied)
    manifest_path = copied / "batch-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["exports"][0]["output_dir"] = str(original / "bae_systems" / "geo_prov")
    manifest.pop("batch_digest")
    manifest["batch_digest"] = canonical_digest(manifest)
    _write_bundle(manifest_path, manifest)
    (copied / "bae_systems" / "geo_prov" / "claims-boundary.md").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="digest mismatch"):
        verify_partner_screening_batch(copied)


def test_verify_cli_returns_nonzero_on_tamper(tmp_path, capsys):
    out = tmp_path / "package"
    export_partner_screening_package(_geo_bundle(), out, partner="BAE_SYSTEMS")
    (out / "claims-boundary.md").write_text("tampered\n", encoding="utf-8")

    rc = verify_main(["--package", str(out)])

    captured = capsys.readouterr()
    assert rc == 1
    assert '"status": "FAIL"' in captured.err
    assert "digest mismatch" in captured.err

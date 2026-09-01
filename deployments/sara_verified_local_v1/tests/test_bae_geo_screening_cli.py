from __future__ import annotations

import json

from worldshepherd_sara.bae_geo_screening_cli import REQUIRED_OUTPUTS, export_screening_package
from worldshepherd_sara.geo_provenance import build_geo_prov_bundle


def test_bae_geo_screening_export_writes_sanitized_partner_package(tmp_path):
    bundle = build_geo_prov_bundle(
        software_commit="test-commit",
        executed_utc="2026-09-01T16:00:00Z",
        operator="pytest",
    )
    manifest = export_screening_package(bundle, tmp_path)

    for filename in REQUIRED_OUTPUTS:
        assert (tmp_path / filename).is_file(), filename

    assert manifest["schema"] == "WS-BAE-GEO-SCREENING-MANIFEST-V1"
    assert manifest["package_id"] == "WS-BAE-GEO-SCREENING-BUNDLE-001"
    assert manifest["source_bundle_digest"] == bundle["bundle_digest"]
    assert sorted(manifest["output_files"]) == sorted(REQUIRED_OUTPUTS - {"manifest.json"})
    assert set(manifest["artifact_digests"]) == REQUIRED_OUTPUTS
    assert all(value.startswith("sha256:") for value in manifest["artifact_digests"].values())

    summary = json.loads((tmp_path / "qualification-summary.json").read_text())
    assert summary["requirement_delta_id"] == "PRE-RD-2026-0020"
    assert summary["test_id"] == "WS-GEO-PROV-001A"
    assert summary["evidence_scope"] == "SIMULATION"
    assert summary["capability_status"] == "SIMULATED_ONLY"
    assert any(item["case"] == "BAE_validation" and item["result"] == "NOT_PERFORMED" for item in summary["negative_evidence_retained"])
    assert "RIVETS" in summary["strongest_bae_pathway"]

    overlay = json.loads((tmp_path / "bae-evidence-overlay.json").read_text())
    assert overlay["schema"] == "WS-BAE-GEO-EVIDENCE-OVERLAY-V1"
    assert "C5ISR" in overlay["overlay"]["bae_lane"]
    assert "SARA" in overlay["overlay"]["worldshepherd_asset"]

    package_text = "\n".join(path.read_text() for path in tmp_path.iterdir() if path.is_file())
    assert "Current maturity remains" in package_text
    assert "does not establish" in package_text
    assert "BAE Systems interest" in package_text
    assert "CMMC conformity" in package_text
    assert "NIST SP 800-171" in package_text
    assert "FIELD_VALIDATED" not in package_text
    assert "SUPPLIER_APPROVED" not in package_text


def test_bae_geo_screening_export_rejects_missing_claim_boundary(tmp_path):
    bundle = build_geo_prov_bundle(
        software_commit="test-commit",
        executed_utc="2026-09-01T16:00:00Z",
        operator="pytest",
    )
    bundle["claims_boundary"] = []

    try:
        export_screening_package(bundle, tmp_path)
    except ValueError as exc:
        assert "missing required claims-boundary" in str(exc)
    else:  # pragma: no cover - explicit failure clarity
        raise AssertionError("expected missing claims-boundary rejection")

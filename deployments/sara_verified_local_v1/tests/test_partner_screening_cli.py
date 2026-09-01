from __future__ import annotations

import json

from worldshepherd_sara.geo_provenance import build_geo_prov_bundle
from worldshepherd_sara.partner_screening_cli import REQUIRED_OUTPUTS, export_partner_screening_package


def _bundle():
    return build_geo_prov_bundle(
        software_commit="test-commit",
        executed_utc="2026-09-01T16:05:00Z",
        operator="pytest",
    )


def test_partner_screening_exports_bae_package_from_geo_bundle(tmp_path):
    bundle = _bundle()
    manifest = export_partner_screening_package(bundle, tmp_path, partner="BAE_SYSTEMS")

    for filename in REQUIRED_OUTPUTS:
        assert (tmp_path / filename).is_file(), filename

    assert manifest["schema"] == "WS-PARTNER-SCREENING-MANIFEST-V1"
    assert manifest["partner_id"] == "BAE_SYSTEMS"
    assert manifest["source_bundle_digest"] == bundle["bundle_digest"]
    assert set(manifest["artifact_digests"]) == REQUIRED_OUTPUTS
    assert all(value.startswith("sha256:") for value in manifest["artifact_digests"].values())

    summary = json.loads((tmp_path / "qualification-summary.json").read_text())
    assert summary["partner_id"] == "BAE_SYSTEMS"
    assert summary["requirement_delta_id"] == "PRE-RD-2026-0020"
    assert summary["test_id"] == "WS-GEO-PROV-001A"
    assert summary["evidence_scope"] == "SIMULATION"
    assert summary["capability_status"] == "SIMULATED_ONLY"
    assert any(item["case"] == "BAE_validation" and item["result"] == "NOT_PERFORMED" for item in summary["negative_evidence_retained"])

    overlay = json.loads((tmp_path / "partner-evidence-overlay.json").read_text())
    assert overlay["schema"] == "WS-PARTNER-EVIDENCE-OVERLAY-V1"
    assert overlay["partner_id"] == "BAE_SYSTEMS"
    assert "RIVETS" in overlay["screening_pathways"]
    assert "C5ISR" in overlay["business_lanes"]
    assert "SARA" in overlay["worldshepherd_assets_or_lanes"]

    package_text = "\n".join(path.read_text() for path in tmp_path.iterdir() if path.is_file())
    assert "partner-screening package" in package_text
    assert "does not establish partner interest" in package_text
    assert "NIST SP 800-171" in package_text
    assert "DFARS" in package_text
    assert "FIELD_VALIDATED" not in package_text
    assert "SUPPLIER_APPROVED" not in package_text


def test_partner_screening_exports_generic_prime_without_bae_overlay(tmp_path):
    bundle = _bundle()
    bundle.pop("bae_evidence_overlay", None)

    manifest = export_partner_screening_package(bundle, tmp_path, partner="GENERIC_PRIME")

    assert manifest["partner_id"] == "GENERIC_PRIME"
    overlay = json.loads((tmp_path / "partner-evidence-overlay.json").read_text())
    assert overlay["partner_id"] == "GENERIC_PRIME"
    assert "technology scouting" in overlay["screening_pathways"]
    assert "mission engineering" in overlay["business_lanes"]
    assert overlay["requirement_delta_id"] == "PRE-RD-2026-0020"


def test_partner_screening_rejects_missing_claim_boundary(tmp_path):
    bundle = _bundle()
    bundle["claims_boundary"] = []

    try:
        export_partner_screening_package(bundle, tmp_path, partner="BAE_SYSTEMS")
    except ValueError as exc:
        assert "missing claims_boundary" in str(exc)
    else:  # pragma: no cover - explicit failure clarity
        raise AssertionError("expected missing claims_boundary rejection")


def test_partner_screening_rejects_false_partner_assertion(tmp_path):
    bundle = _bundle()
    bundle["claims_boundary"].append("BAE_VALIDATED")

    try:
        export_partner_screening_package(bundle, tmp_path, partner="BAE_SYSTEMS")
    except ValueError as exc:
        assert "prohibited assertion" in str(exc)
    else:  # pragma: no cover - explicit failure clarity
        raise AssertionError("expected prohibited assertion rejection")

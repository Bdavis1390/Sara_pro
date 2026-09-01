from __future__ import annotations

import copy
import json
from pathlib import Path

from worldshepherd_sara.partner_screening_cli import REQUIRED_OUTPUTS, export_partner_screening_package
from worldshepherd_sara.pre_bloom_cli import build_bloom

ROOT = Path(__file__).resolve().parents[1]

LANE_MATRIX = {
    "apnt": {
        "requirement_id": "PRE-RD-2026-0001",
        "required_lane": "APNT",
    },
    "ddil": {
        "requirement_id": "PRE-RD-2026-0001",
        "required_lane": "DDIL",
    },
    "mission": {
        "requirement_id": "PRE-RD-2026-0013",
        "required_lane": "mission replay",
    },
    "fusion": {
        "requirement_id": "PRE-RD-2026-0014",
        "required_lane": "distributed sensing",
    },
    "rf": {
        "requirement_id": "PRE-RD-2026-0015",
        "required_lane": "RF",
    },
    "cbm": {
        "requirement_id": "PRE-RD-2026-0016",
        "required_lane": "CBM+",
    },
    "manufacturing": {
        "requirement_id": "PRE-RD-2026-0017",
        "required_lane": "DED",
    },
    "edge": {
        "requirement_id": "PRE-RD-2026-0018",
        "required_lane": "edge AI",
    },
    "ddil_rejoin": {
        "requirement_id": "PRE-RD-2026-0019",
        "required_lane": "DDIL",
    },
}


def _screening_ready_copy(bundle: dict) -> dict:
    """Preserve source boundaries while adding one explicit matrix boundary.

    Some early PRE bundles use short "No ... claim" wording. The generic exporter
    already preserves those source lines, and this fixture adds a uniform explicit
    non-claim sentence so the matrix focuses on cross-lane package compatibility.
    """
    value = copy.deepcopy(bundle)
    value.setdefault("claims_boundary", []).append(
        "Matrix screening export does not establish partner validation, supplier approval, certification, field performance, hardware performance, or operational authority."
    )
    return value


def test_partner_screening_matrix_exports_major_non_geo_pre_lanes(tmp_path):
    bloom_dir = tmp_path / "bloom"
    index = build_bloom(
        fixtures=ROOT / "fixtures",
        out=bloom_dir,
        software_commit="test-commit",
        executed_utc="2026-09-01T16:10:00Z",
        operator="pytest-partner-screening-matrix",
    )

    for lane, expected in LANE_MATRIX.items():
        bundle_path = bloom_dir / f"{lane}_qualification_bundle.json"
        assert bundle_path.is_file(), lane
        bundle = json.loads(bundle_path.read_text())
        assert bundle["requirement"]["requirement_delta_id"] == expected["requirement_id"]
        assert expected["required_lane"] in bundle["requirement"]["affected_lanes"]
        assert bundle["bundle_digest"] == index["bundle_digests"][lane]
        assert bundle["evidence"][0]["result"] == "PASS"

        for partner in ("BAE_SYSTEMS", "GENERIC_PRIME"):
            out = tmp_path / "screening" / lane / partner.lower()
            manifest = export_partner_screening_package(_screening_ready_copy(bundle), out, partner=partner)

            assert manifest["schema"] == "WS-PARTNER-SCREENING-MANIFEST-V1"
            assert manifest["partner_id"] == partner
            assert set(manifest["artifact_digests"]) == REQUIRED_OUTPUTS
            assert all(value.startswith("sha256:") for value in manifest["artifact_digests"].values())

            summary = json.loads((out / "qualification-summary.json").read_text())
            assert summary["requirement_delta_id"] == expected["requirement_id"]
            assert summary["test_id"] == bundle["evidence"][0]["test_id"]
            assert summary["evidence_scope"] == bundle["evidence"][0]["evidence_scope"]
            assert summary["capability_status"] == bundle["evidence"][0]["capability_status"]
            assert summary["result"] == "PASS"
            assert "Matrix screening export does not establish" in "\n".join(summary["claim_boundary"])

            overlay = json.loads((out / "partner-evidence-overlay.json").read_text())
            assert overlay["partner_id"] == partner
            assert overlay["requirement_delta_id"] == expected["requirement_id"]
            assert overlay["test_id"] == bundle["evidence"][0]["test_id"]
            assert overlay["claim_boundary_note"].startswith("The overlay is a screening map only")

            package_text = "\n".join(path.read_text() for path in out.iterdir() if path.is_file())
            assert "does not establish partner interest" in package_text
            assert "SUPPLIER_APPROVED" not in package_text
            assert "FIELD_VALIDATED" not in package_text
            assert "PARTNER_VALIDATED" not in package_text

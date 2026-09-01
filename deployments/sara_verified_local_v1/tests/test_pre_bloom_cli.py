from __future__ import annotations

import json
from pathlib import Path

from worldshepherd_sara.pre_bloom_cli import build_bloom

ROOT = Path(__file__).resolve().parents[1]


def test_full_bloom_compiler_emits_cross_domain_evidence_readiness_horizons_and_provenance(tmp_path):
    out = tmp_path / "bloom"
    index = build_bloom(
        fixtures=ROOT / "fixtures",
        out=out,
        software_commit="test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    expected_bundles = {
        "apnt", "mbse", "ietm", "ade", "mission", "fusion", "rf", "cbm",
        "manufacturing", "ddil", "edge", "ddil_rejoin", "geo_prov",
    }
    assert expected_bundles.issubset(index["bundle_digests"])
    assert all(not failures for failures in index["failures"].values())
    assert all(index["custody_verification"].values())
    assert (out / "capability_readiness_ledger.json").is_file()
    assert (out / "capability_horizons.json").is_file()
    assert (out / "software_provenance.json").is_file()
    assert (out / "geo_prov_qualification_bundle.json").is_file()

    geo = json.loads((out / "geo_prov_qualification_bundle.json").read_text())
    assert geo["requirement"]["requirement_delta_id"] == "PRE-RD-2026-0020"
    assert geo["evidence"][0]["test_id"] == "WS-GEO-PROV-001A"
    assert geo["evidence"][0]["evidence_scope"] == "SIMULATION"
    assert geo["evidence"][0]["capability_status"] == "SIMULATED_ONLY"
    assert geo["geo_provenance"]["change_event"]["null_control_passed"] is True
    assert "BAE_validation" in geo["evidence"][0]["negative_evidence"][2]["case"]
    assert any("No BAE interest" in item for item in geo["claims_boundary"])
    assert "geo_prov" in index["bundle_digests"]
    assert "geo_provenance_replay_bundle" in index["bloom_extensions"]

    provenance = json.loads((out / "software_provenance.json").read_text())
    assert provenance["attestation_state"] == "INTERNAL_UNSIGNED"
    policy = provenance["metadata"]["build_policy_inputs"]
    for name in ("pyproject.toml", "constraints-runtime.txt", "constraints-ci.txt", "Dockerfile"):
        assert policy["files"][name].startswith("sha256:")
    assert "@sha256:" in policy["container_base_reference"]
    assert "build_policy_input_digests" in index["bloom_extensions"]

    horizons = json.loads((out / "capability_horizons.json").read_text())
    assert {record["horizon"] for record in horizons["records"]} >= {"0-90D", "3-12M", "12-24M_PLUS"}

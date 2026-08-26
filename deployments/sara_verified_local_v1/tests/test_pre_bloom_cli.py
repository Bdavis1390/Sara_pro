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
        "manufacturing", "ddil", "edge", "ddil_rejoin",
    }
    assert expected_bundles.issubset(index["bundle_digests"])
    assert all(not failures for failures in index["failures"].values())
    assert all(index["custody_verification"].values())
    assert (out / "capability_readiness_ledger.json").is_file()
    assert (out / "capability_horizons.json").is_file()
    assert (out / "software_provenance.json").is_file()
    provenance = json.loads((out / "software_provenance.json").read_text())
    assert provenance["attestation_state"] == "INTERNAL_UNSIGNED"
    horizons = json.loads((out / "capability_horizons.json").read_text())
    assert {record["horizon"] for record in horizons["records"]} >= {"0-90D", "3-12M", "12-24M_PLUS"}

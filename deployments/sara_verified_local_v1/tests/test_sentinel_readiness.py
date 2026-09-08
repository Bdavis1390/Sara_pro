import json

from worldshepherd_sara.sentinel_readiness import (
    ALLOWED_DATA_CLASSES,
    EXTERNAL_PREAUTH_CAP_PCT,
    INTERNAL_TARGET_PCT,
    build_readiness_report,
    evaluate_data_boundary,
    external_gate_matrix,
    run_integrity_adversarial_campaign,
    run_scale_campaign,
)
from worldshepherd_sara.sentinel_readiness_cli import build_readiness_bundle


def test_data_boundary_allows_only_public_and_synthetic() -> None:
    for data_class in ("PUBLIC", "SYNTHETIC"):
        decision = evaluate_data_boundary(data_class)
        assert decision.allowed is True
        assert decision.data_class in ALLOWED_DATA_CLASSES

    for data_class in (
        "FCI",
        "CUI",
        "CDI",
        "EXPORT_CONTROLLED",
        "CLASSIFIED",
        "UNKNOWN",
        "UNLISTED",
        "",
    ):
        assert evaluate_data_boundary(data_class).allowed is False


def test_scale_campaign_closes_clean_packages_and_denies_unauthorized_mutation() -> None:
    report = run_scale_campaign(500)
    assert report["pass"] is True
    assert report["closed_cleanly"] == 500
    assert report["false_blocks"] == 0
    assert report["unauthorized_attempts"] == 500
    assert report["unauthorized_authoritative_mutations"] == 0


def test_integrity_adversarial_campaign_closes_all_encoded_failures() -> None:
    report = run_integrity_adversarial_campaign()
    assert report["pass"] is True
    assert report["check_count"] == 8
    assert report["passed_count"] == 8
    assert all(report["checks"].values())


def test_internal_preparation_can_pass_without_promoting_external_readiness() -> None:
    report = build_readiness_report(scale_package_count=250)
    assert report["internal_preparation_score_pct"] >= INTERNAL_TARGET_PCT
    assert report["internal_preparation_gate_pass"] is True
    assert report["integrity_adversarial_campaign"]["pass"] is True
    assert report["external_operational_readiness_cap_pct"] == EXTERNAL_PREAUTH_CAP_PCT
    assert report["external_operational_gate_pass"] is False
    assert report["decision"] == "INTERNAL_PREPARATION_GATE_PASS_EXTERNAL_GATES_OPEN"
    assert "does not establish" in report["claims_boundary"].lower()


def test_external_gates_are_not_self_closeable() -> None:
    matrix = external_gate_matrix()
    assert matrix["current_external_readiness_cap_pct"] == EXTERNAL_PREAUTH_CAP_PCT
    assert len(matrix["gates"]) == 5
    assert all(item["self_close_allowed"] is False for item in matrix["gates"])
    assert matrix["gates"][0]["state"] == "MISSING"


def test_readiness_bundle_is_machine_readable_and_fail_closed(tmp_path) -> None:
    out = tmp_path / "sentinel-readiness"
    index = build_readiness_bundle(
        out=out,
        software_commit="test-commit",
        executed_utc="2026-09-08T02:10:00Z",
        operator="pytest",
        scale_package_count=100,
    )
    assert index["internal_preparation_gate_pass"] is True
    assert index["external_operational_gate_pass"] is False
    assert index["index_digest"].startswith("sha256:")
    expected = {
        "readiness-report.json",
        "external-gate-matrix.json",
        "scale-campaign.json",
        "integrity-adversarial-campaign.json",
        "data-boundary-report.json",
        "readiness-evidence-index.json",
        "claims-boundary.md",
    }
    assert {path.name for path in out.iterdir()} == expected

    report = json.loads((out / "readiness-report.json").read_text(encoding="utf-8"))
    assert report["internal_preparation_gate_pass"] is True
    assert report["integrity_adversarial_campaign"]["pass"] is True
    assert report["external_operational_gate_pass"] is False
    assert report["external_operational_readiness_cap_pct"] == 55.0
    assert report["software_commit"] == "test-commit"

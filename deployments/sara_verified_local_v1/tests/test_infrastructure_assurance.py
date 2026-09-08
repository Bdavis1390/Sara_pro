import json

from worldshepherd_sara.infrastructure_assurance import (
    PackageState,
    authorize_configuration_change,
    build_synthetic_packages,
    close_package,
    ingest_evidence,
    run_gate,
)
from worldshepherd_sara.infrastructure_assurance import _valid_evidence
from worldshepherd_sara.sentinel_infrastructure_cli import build_evidence_bundle


def test_sentinel_g1_campaign_passes_all_ten_failure_classes() -> None:
    report = run_gate()
    assert report.pass_gate is True
    assert report.metrics["failure_class_count"] == 10
    assert report.metrics["detected_failure_count"] == 10
    assert report.metrics["safe_state_preserved_count"] == 10
    assert report.metrics["unauthorized_authoritative_mutations"] == 0
    assert report.bundle_digest.startswith("sha256:")
    assert "does not establish Sentinel fitness" in report.claims_boundary
    assert {item.failure_id for item in report.failure_results} == {
        "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"
    }


def test_unauthorized_configuration_change_is_denied_without_mutation() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    event = authorize_configuration_change(
        state,
        actor="field-actor",
        role="FIELD_OPERATOR",
        new_baseline="BL-999",
    )
    assert event.decision == "DENY"
    assert state.current_baseline == "BL-001"
    assert state.config_mutations == 0
    assert state.events[-1]["event_type"] == "configuration_change_denied"


def test_closure_requires_complete_clean_authoritative_evidence() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    for evidence_type in package.required_evidence_types:
        record = _valid_evidence(
            state,
            evidence_id=f"E-{evidence_type}",
            evidence_type=evidence_type,
        )
        accepted, findings = ingest_evidence(state, record)
        assert accepted is True
        assert findings == ()

    closed, blockers = close_package(state)
    assert closed is True
    assert blockers == ()
    assert state.package.state == "CLOSED"


def test_stale_evidence_blocks_authoritative_acceptance_and_closure() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-002")
    stale = _valid_evidence(
        state,
        evidence_id="E-stale",
        evidence_type="inspection",
        baseline_id="BL-001",
    )
    accepted, findings = ingest_evidence(state, stale)
    assert accepted is False
    assert "STALE_BASELINE" in findings
    assert "inspection" not in state.authoritative_evidence

    closed, blockers = close_package(state)
    assert closed is False
    assert state.package.state == "BLOCKED"
    assert "UNRESOLVED_ISSUES" in blockers


def test_evidence_bundle_is_machine_readable_and_claims_controlled(tmp_path) -> None:
    out = tmp_path / "sentinel-g1"
    index = build_evidence_bundle(
        out=out,
        campaign_id="WS-SENTINEL-DEMO-G1-TEST",
        software_commit="test-commit",
        executed_utc="2026-09-08T00:00:00Z",
        operator="pytest",
    )
    assert index["pass_gate"] is True
    assert index["index_digest"].startswith("sha256:")
    expected = {
        "scenario-manifest.json",
        "gate-report.json",
        "failure-results.json",
        "software-provenance.json",
        "evidence-index.json",
        "claims-boundary.md",
    }
    assert {path.name for path in out.iterdir()} == expected

    gate = json.loads((out / "gate-report.json").read_text(encoding="utf-8"))
    assert gate["schema"] == "WS-SENTINEL-G1-REPORT-V1"
    assert gate["pass_gate"] is True
    assert gate["metrics"]["failure_class_count"] == 10
    assert gate["evidence_status"] == "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE"
    assert "does not establish Sentinel fitness" in gate["claims_boundary"]

    scenario = json.loads((out / "scenario-manifest.json").read_text(encoding="utf-8"))
    assert scenario["synthetic_only"] is True
    assert scenario["segment_count"] == 12
    assert scenario["work_package_count"] == 24
    assert len(scenario["failure_classes"]) == 10

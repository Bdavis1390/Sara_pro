import json
from dataclasses import replace

import pytest
from fastapi import HTTPException

from worldshepherd_sara.infrastructure_assurance import (
    PackageState,
    authorize_configuration_change,
    build_synthetic_packages,
    close_package,
    ingest_evidence,
    issue_authorization_capability,
    resolve_issue,
    run_authorization_integrity_selftest,
    run_evidence_immutability_selftest,
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


def test_claimed_authority_role_without_capability_is_denied() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    event = authorize_configuration_change(
        state,
        actor="unverified-caller",
        role=package.authority_required,
        new_baseline="BL-002",
    )
    assert event.decision == "DENY"
    assert state.current_baseline == "BL-001"
    assert state.config_mutations == 0


class _DuckTypedForgedCapability:
    actor = "SARA_AUTHENTICATED_ADMIN"
    role = "PROGRAM_INTEGRATION_AUTHORITY"

    def __init__(self, target_id: str, action: str) -> None:
        self.target_id = target_id
        self.action = action

    def valid_for(self, **_kwargs) -> bool:
        return True


def test_duck_typed_capability_cannot_dispatch_attacker_verifier() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    forged_change = _DuckTypedForgedCapability(package.package_id, "CONFIGURATION_CHANGE")
    event = authorize_configuration_change(
        state,
        actor=forged_change.actor,
        role=forged_change.role,
        new_baseline="BL-999",
        capability=forged_change,
    )
    assert event.decision == "DENY"
    assert state.current_baseline == "BL-001"
    assert state.config_mutations == 0

    state.issues.append("SYNTHETIC_OPEN_ISSUE")
    forged_resolution = _DuckTypedForgedCapability(package.package_id, "ISSUE_RESOLUTION")
    resolved = resolve_issue(
        state,
        issue="SYNTHETIC_OPEN_ISSUE",
        actor=forged_resolution.actor,
        role=forged_resolution.role,
        rationale="attacker-controlled verifier",
        capability=forged_resolution,
    )
    assert resolved is False
    assert "SYNTHETIC_OPEN_ISSUE" in state.issues


def test_authenticated_capability_is_bearer_validated_and_target_scoped(monkeypatch) -> None:
    admin_token = "admin-token-" + "a" * 24
    relay_token = "relay-token-" + "b" * 24
    monkeypatch.setenv("SARA_ADMIN_TOKEN", admin_token)
    monkeypatch.setenv("SARA_RELAY_TOKEN", relay_token)

    packages = build_synthetic_packages(2)
    capability = issue_authorization_capability(
        authorization=f"Bearer {admin_token}",
        target_id=packages[0].package_id,
        authority_role=packages[0].authority_required,
    )
    assert capability.actor == "SARA_AUTHENTICATED_ADMIN"
    assert capability.target_id == packages[0].package_id
    assert capability.action == "CONFIGURATION_CHANGE"

    state = PackageState(package=packages[0], current_baseline="BL-001")
    allowed = authorize_configuration_change(
        state,
        actor=capability.actor,
        role=packages[0].authority_required,
        new_baseline="BL-002",
        capability=capability,
    )
    assert allowed.decision == "ALLOW"
    assert state.current_baseline == "BL-002"

    other_state = PackageState(package=packages[1], current_baseline="BL-001")
    denied = authorize_configuration_change(
        other_state,
        actor=capability.actor,
        role=packages[1].authority_required,
        new_baseline="BL-002",
        capability=capability,
    )
    assert denied.decision == "DENY"
    assert other_state.current_baseline == "BL-001"

    # Regression for the P1 copy/retarget exploit: dataclasses.replace preserves the
    # original signature, but changing the target makes that signature invalid.
    retargeted = replace(capability, target_id=packages[1].package_id)
    retarget_denied = authorize_configuration_change(
        other_state,
        actor=retargeted.actor,
        role=packages[1].authority_required,
        new_baseline="BL-003",
        capability=retargeted,
    )
    assert retarget_denied.decision == "DENY"
    assert other_state.current_baseline == "BL-001"
    assert other_state.config_mutations == 0

    # Action is part of the signed payload as well; a configuration capability cannot
    # be repurposed as an issue-resolution capability.
    action_replaced = replace(capability, action="ISSUE_RESOLUTION")
    assert action_replaced.valid_for(
        actor=action_replaced.actor,
        role=action_replaced.role,
        target_id=action_replaced.target_id,
        action="ISSUE_RESOLUTION",
    ) is False

    with pytest.raises(HTTPException):
        issue_authorization_capability(
            authorization="Bearer " + "x" * 32,
            target_id=packages[0].package_id,
        )


def test_authorization_and_evidence_hardening_selftests_pass() -> None:
    authorization = run_authorization_integrity_selftest()
    evidence = run_evidence_immutability_selftest()
    assert len(authorization) == 5
    assert all(authorization.values())
    assert authorization["capability_retarget_tamper_rejected"] is True
    assert authorization["capability_action_binding_enforced"] is True
    assert len(evidence) == 3
    assert all(evidence.values())


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


def test_closure_rejects_never_ingested_authoritative_replacement() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    for evidence_type in package.required_evidence_types:
        accepted, findings = ingest_evidence(
            state,
            _valid_evidence(
                state,
                evidence_id=f"ACCEPTED-{evidence_type}",
                evidence_type=evidence_type,
            ),
        )
        assert accepted is True
        assert findings == ()

    forged_replacement = _valid_evidence(
        state,
        evidence_id="NEVER-INGESTED-DESIGN",
        evidence_type="design",
        version=99,
    )
    state.authoritative_evidence["design"] = forged_replacement
    state.all_evidence[forged_replacement.evidence_id] = forged_replacement
    accepted_binding = state._accepted_history["design"][-1]
    state._accepted_history["design"] = (
        replace(
            accepted_binding,
            evidence_id=forged_replacement.evidence_id,
            version=forged_replacement.version,
            digest=forged_replacement.digest,
        ),
    )

    closed, blockers = close_package(state)
    assert closed is False
    assert "INVALID_AUTHORITATIVE_EVIDENCE:design" in blockers


def test_closure_rejects_authoritative_downgrade_after_valid_supersession() -> None:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")

    design_v1 = _valid_evidence(
        state,
        evidence_id="DESIGN-V1",
        evidence_type="design",
        version=1,
    )
    accepted_v1, _ = ingest_evidence(state, design_v1)
    assert accepted_v1 is True

    design_v2 = _valid_evidence(
        state,
        evidence_id="DESIGN-V2",
        evidence_type="design",
        version=2,
        supersedes="DESIGN-V1",
    )
    accepted_v2, findings_v2 = ingest_evidence(state, design_v2)
    assert accepted_v2 is True
    assert findings_v2 == ()

    for evidence_type in ("inspection", "as_built"):
        accepted, findings = ingest_evidence(
            state,
            _valid_evidence(
                state,
                evidence_id=f"ACCEPTED-{evidence_type}",
                evidence_type=evidence_type,
            ),
        )
        assert accepted is True
        assert findings == ()

    state.authoritative_evidence["design"] = design_v1
    closed, blockers = close_package(state)
    assert closed is False
    assert "INVALID_AUTHORITATIVE_EVIDENCE:design" in blockers


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

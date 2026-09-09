import pytest

from worldshepherd_sara.infrastructure_assurance import (
    PackageState,
    _append_issue,
    _custody,
    _valid_evidence,
    build_synthetic_packages,
    close_package,
    ingest_evidence,
    issue_authorization_capability,
    resolve_issue,
)


def _complete_state(prefix: str) -> PackageState:
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    for evidence_type in package.required_evidence_types:
        accepted, findings = ingest_evidence(
            state,
            _valid_evidence(
                state,
                evidence_id=f"{prefix}-{evidence_type}",
                evidence_type=evidence_type,
            ),
        )
        assert accepted is True
        assert findings == ()
    return state


def test_package_state_custody_registration_is_one_shot() -> None:
    state = PackageState(package=build_synthetic_packages(1)[0], current_baseline="BL-001")
    bad = _valid_evidence(state, evidence_id="RESET-BAD", evidence_type="design", valid=False)
    accepted, findings = ingest_evidence(state, bad)
    assert accepted is False
    assert "SOURCE_MARKED_INVALID" in findings

    state.package.required_evidence_types = ()
    state.issues.clear()

    with pytest.raises(RuntimeError, match="already registered|reinitial"):
        state.__post_init__()


def test_package_state_subclasses_are_rejected_by_engine_custody() -> None:
    class ForgedPackageState(PackageState):
        def __hash__(self) -> int:
            return 1

        def __eq__(self, _other: object) -> bool:
            return True

    forged = ForgedPackageState(
        package=build_synthetic_packages(1)[0],
        current_baseline="BL-001",
    )
    with pytest.raises(RuntimeError, match="exact|module-owned|PackageState"):
        _custody(forged)


def test_evidence_ingestion_fails_closed_after_package_closure() -> None:
    state = _complete_state("POST-CLOSE")
    closed, blockers = close_package(state)
    assert closed is True
    assert blockers == ()

    current = state.authoritative_evidence["design"]
    replacement = _valid_evidence(
        state,
        evidence_id="POST-CLOSE-design-v2",
        evidence_type="design",
        version=current.version + 1,
        supersedes=current.evidence_id,
    )
    accepted, findings = ingest_evidence(state, replacement)

    assert accepted is False
    assert "PACKAGE_CLOSED" in findings
    assert state.authoritative_evidence["design"].evidence_id == current.evidence_id


def test_resolved_issue_provenance_is_retained_in_engine_custody(monkeypatch) -> None:
    admin_token = "admin-token-" + "a" * 24
    relay_token = "relay-token-" + "b" * 24
    monkeypatch.setenv("SARA_ADMIN_TOKEN", admin_token)
    monkeypatch.setenv("SARA_RELAY_TOKEN", relay_token)

    state = _complete_state("RESOLVED-CUSTODY")
    issue = "SYNTHETIC_RESOLUTION_BLOCKER"
    _append_issue(state, issue)

    capability = issue_authorization_capability(
        authorization=f"Bearer {admin_token}",
        target_id=state.package.package_id,
        authority_role=state.package.authority_required,
        action="ISSUE_RESOLUTION",
    )
    assert resolve_issue(
        state,
        issue=issue,
        actor=capability.actor,
        role=capability.role,
        rationale="synthetic regression resolution",
        capability=capability,
    ) is True

    custody = _custody(state)
    assert hasattr(custody, "resolved_issues")
    assert custody.resolved_issues
    latest = custody.resolved_issues[-1]
    assert latest["issue"] == issue
    assert latest["actor"] == capability.actor
    assert latest["rationale"] == "synthetic regression resolution"

    state.events.clear()
    closed, blockers = close_package(state)
    assert closed is True
    assert blockers == ()

import importlib
import subprocess
import sys

import pytest

import worldshepherd_sara.infrastructure_assurance as assurance
from worldshepherd_sara.infrastructure_assurance import (
    PackageState,
    _append_issue,
    _custody,
    _resolved_issue_snapshot,
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


def _resolve_synthetic_issue(state: PackageState, monkeypatch, suffix: str) -> str:
    admin_token = "admin-token-" + suffix * 24
    relay_token = "relay-token-" + suffix.upper() * 24
    monkeypatch.setenv("SARA_ADMIN_TOKEN", admin_token)
    monkeypatch.setenv("SARA_RELAY_TOKEN", relay_token)
    issue = f"SYNTHETIC_{suffix}_BLOCKER"
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
        rationale="authorized synthetic resolution",
        capability=capability,
    ) is True
    return issue


def test_resolved_issue_provenance_snapshot_is_detached(monkeypatch) -> None:
    state = _complete_state("RESOLVED-CUSTODY")
    issue = _resolve_synthetic_issue(state, monkeypatch, "a")

    custody = _custody(state)
    assert not hasattr(custody, "resolved_issues")

    snapshot = _resolved_issue_snapshot(state)
    assert snapshot and snapshot[-1]["issue"] == issue
    snapshot[-1]["rationale"] = "caller-forged detached copy"

    fresh = _resolved_issue_snapshot(state)
    assert fresh[-1]["rationale"] == "authorized synthetic resolution"

    closed, blockers = close_package(state)
    assert closed is True
    assert blockers == ()


def test_resolution_signing_secret_is_not_returned_by_custody(monkeypatch) -> None:
    state = _complete_state("RESOLUTION-KEY")
    _resolve_synthetic_issue(state, monkeypatch, "b")
    custody = _custody(state)
    assert not hasattr(custody, "resolution_key")
    assert not hasattr(custody, "resolved_issues")


def test_direct_legacy_import_remains_synthetic_not_production_authority() -> None:
    code = r'''
import tomllib
from pathlib import Path
from worldshepherd_sara import infrastructure_assurance_legacy as legacy

state = legacy.PackageState(
    package=legacy.build_synthetic_packages(1)[0],
    current_baseline="BL-001",
)
# The preserved legacy implementation may execute only as explicitly imported
# synthetic code. It must not control the installed production Sentinel route.
assert state.package is not None
pyproject = Path("pyproject.toml")
scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
assert scripts["ws-sentinel-readiness"] == "worldshepherd_sara.sentinel_authority_cli:main"
assert scripts["ws-sentinel-infrastructure"] == "worldshepherd_sara.sentinel_authority_cli:main"
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_reload_cannot_restore_vulnerable_implementation_when_hardening_overlay_is_explicitly_loaded() -> None:
    from worldshepherd_sara import infrastructure_assurance_legacy as legacy

    before = legacy.ingest_evidence
    reloaded = importlib.reload(legacy)
    assert reloaded is legacy
    assert legacy.ingest_evidence is before
    assert legacy.ingest_evidence is assurance.ingest_evidence

    state = legacy.PackageState(
        package=legacy.build_synthetic_packages(1)[0],
        current_baseline="BL-001",
    )
    with pytest.raises(RuntimeError, match="already registered|reinitial"):
        state.__post_init__()


def test_hardened_ingest_and_close_do_not_capture_legacy_callables() -> None:
    for function in (assurance.ingest_evidence, assurance.close_package):
        closure = function.__closure__ or ()
        assert not any(callable(cell.cell_contents) for cell in closure)


def test_hardened_module_does_not_expose_vulnerable_original_handles() -> None:
    assert not hasattr(assurance, "_ORIGINAL_INGEST_EVIDENCE")
    assert not hasattr(assurance, "_ORIGINAL_CLOSE_PACKAGE")

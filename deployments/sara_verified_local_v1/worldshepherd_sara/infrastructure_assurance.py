from __future__ import annotations

import hashlib
import hmac
import json
import weakref
from typing import Any, Callable

from . import infrastructure_assurance_legacy as _legacy

# Re-export the legacy implementation surface first; the bounded hardening
# overrides below replace only the four P1-affected state transitions.
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

PackageState = _legacy.PackageState
_EngineCustody = _legacy._EngineCustody
AuthorizationCapability = _legacy.AuthorizationCapability
EvidenceRecord = _legacy.EvidenceRecord

_IDENTITY_CUSTODY: dict[int, tuple[weakref.ReferenceType[PackageState], _EngineCustody]] = {}


def _cleanup_identity_custody(key: int, state_ref: weakref.ReferenceType[PackageState]) -> None:
    current = _IDENTITY_CUSTODY.get(key)
    if current is not None and current[0] is state_ref:
        _IDENTITY_CUSTODY.pop(key, None)


def _register_package_state(state: PackageState) -> None:
    if type(state) is not PackageState:
        return
    key = id(state)
    existing = _IDENTITY_CUSTODY.get(key)
    if existing is not None and existing[0]() is state:
        raise RuntimeError("package state is already registered; custody cannot be reinitialized")
    if existing is not None and existing[0]() is not None:
        raise RuntimeError("package state identity collision")

    custody = _EngineCustody(
        package_id=state.package.package_id,
        authority_required=state.package.authority_required,
        required_evidence_types=tuple(state.package.required_evidence_types),
        current_baseline=state.current_baseline,
        history_key=_legacy.secrets.token_bytes(32),
    )
    custody.issue_history = []
    custody.resolved_issues = []

    state_ref = weakref.ref(
        state,
        lambda ref, identity=key: _cleanup_identity_custody(identity, ref),
    )
    _IDENTITY_CUSTODY[key] = (state_ref, custody)


PackageState.__post_init__ = _register_package_state


def _custody(state: PackageState) -> _EngineCustody:
    if type(state) is not PackageState:
        raise RuntimeError("engine custody requires exact module-owned PackageState")
    entry = _IDENTITY_CUSTODY.get(id(state))
    if entry is None or entry[0]() is not state:
        raise RuntimeError("package state is not registered with identity-bound engine custody")
    return entry[1]


_legacy._custody = _custody


def _append_issue(state: PackageState, finding: str) -> None:
    custody = _custody(state)
    if finding not in custody.open_issues:
        custody.open_issues.append(finding)
    if finding not in custody.issue_history:
        custody.issue_history.append(finding)
    if finding not in state.issues:
        state.issues.append(finding)


_legacy._append_issue = _append_issue


def _build_hardened_ingest(
    legacy_ingest: Callable[[PackageState, EvidenceRecord], tuple[bool, tuple[str, ...]]],
) -> Callable[[PackageState, EvidenceRecord], tuple[bool, tuple[str, ...]]]:
    def hardened_ingest(
        state: PackageState, record: EvidenceRecord
    ) -> tuple[bool, tuple[str, ...]]:
        custody = _custody(state)
        if custody.closed:
            findings = ("PACKAGE_CLOSED",)
            state.record(
                "evidence_rejected_after_closure",
                evidence_id=record.evidence_id,
                findings=list(findings),
            )
            return False, findings
        return legacy_ingest(state, record)

    return hardened_ingest


ingest_evidence = _build_hardened_ingest(_legacy.ingest_evidence)
_legacy.ingest_evidence = ingest_evidence


def _resolution_payload(entry: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "schema": "WS-SENTINEL-RESOLVED-ISSUE-CUSTODY-V1",
            "issue": entry["issue"],
            "actor": entry["actor"],
            "role": entry["role"],
            "target_id": entry["target_id"],
            "action": entry["action"],
            "rationale": entry["rationale"],
            "previous_tag": entry["previous_tag"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolution_tag(custody: _EngineCustody, entry: dict[str, Any]) -> str:
    return "hmac-sha256:" + hmac.new(
        custody.history_key,
        _resolution_payload(entry),
        hashlib.sha256,
    ).hexdigest()


def resolve_issue(
    state: PackageState,
    *,
    issue: str,
    actor: str,
    role: str,
    rationale: str,
    capability: AuthorizationCapability | None = None,
) -> bool:
    custody = _custody(state)
    verified_authority = _legacy._capability_valid_for_current_secret(
        capability,
        actor=actor,
        role=custody.authority_required,
        target_id=custody.package_id,
        action="ISSUE_RESOLUTION",
    )
    if not verified_authority:
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            claimed_role=role,
            reason="verified_authorization_capability_required",
        )
        return False
    if custody.closed:
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            verified_role=capability.role,
            reason="closed_package_requires_reopen_workflow",
        )
        return False
    if not rationale.strip():
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            verified_role=capability.role,
            reason="rationale_required",
        )
        return False
    if issue not in custody.open_issues:
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            verified_role=capability.role,
            reason="issue_not_open",
        )
        return False

    previous_tag = custody.resolved_issues[-1]["tag"] if custody.resolved_issues else "GENESIS"
    entry: dict[str, Any] = {
        "issue": issue,
        "actor": actor,
        "role": capability.role,
        "target_id": capability.target_id,
        "action": capability.action,
        "rationale": rationale,
        "previous_tag": previous_tag,
    }
    entry["tag"] = _resolution_tag(custody, entry)
    custody.resolved_issues.append(entry)

    custody.open_issues.remove(issue)
    if issue in state.issues:
        state.issues.remove(issue)
    state.record(
        "issue_resolved",
        issue=issue,
        actor=actor,
        verified_role=capability.role,
        capability_target=capability.target_id,
        capability_action=capability.action,
        rationale=rationale,
        resolution_tag=entry["tag"],
    )
    return True


_legacy.resolve_issue = resolve_issue


def _resolved_issue_custody_valid(state: PackageState) -> bool:
    custody = _custody(state)
    expected_previous = "GENESIS"
    resolved_names: list[str] = []
    for entry in custody.resolved_issues:
        required = {
            "issue",
            "actor",
            "role",
            "target_id",
            "action",
            "rationale",
            "previous_tag",
            "tag",
        }
        if not isinstance(entry, dict) or not required.issubset(entry):
            return False
        if entry["previous_tag"] != expected_previous:
            return False
        expected_tag = _resolution_tag(custody, entry)
        if not hmac.compare_digest(str(entry["tag"]), expected_tag):
            return False
        if entry["target_id"] != custody.package_id or entry["action"] != "ISSUE_RESOLUTION":
            return False
        if not str(entry["rationale"]).strip():
            return False
        expected_previous = str(entry["tag"])
        resolved_names.append(str(entry["issue"]))

    for issue in custody.issue_history:
        if issue not in custody.open_issues and issue not in resolved_names:
            return False
    return True


def _build_hardened_close(
    legacy_close: Callable[[PackageState], tuple[bool, tuple[str, ...]]],
) -> Callable[[PackageState], tuple[bool, tuple[str, ...]]]:
    def hardened_close(state: PackageState) -> tuple[bool, tuple[str, ...]]:
        if not _resolved_issue_custody_valid(state):
            blockers = ("INVALID_RESOLVED_ISSUE_CUSTODY",)
            state.package.state = "BLOCKED"
            state.record("closure_blocked", blockers=list(blockers))
            return False, blockers
        return legacy_close(state)

    return hardened_close


close_package = _build_hardened_close(_legacy.close_package)
_legacy.close_package = close_package

globals().update(
    {
        "_custody": _custody,
        "_append_issue": _append_issue,
        "ingest_evidence": ingest_evidence,
        "resolve_issue": resolve_issue,
        "close_package": close_package,
    }
)

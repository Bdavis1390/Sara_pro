from __future__ import annotations

import hashlib
import hmac
import importlib.abc
import importlib.util
import json
import secrets
import sys
import weakref
from dataclasses import dataclass
from typing import Any

from . import infrastructure_assurance_legacy as _legacy

# Re-export the legacy implementation surface first; bounded hardening below
# replaces the P1-sensitive state transitions and custody boundaries.
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

PackageState = _legacy.PackageState
_EngineCustody = _legacy._EngineCustody
AuthorizationCapability = _legacy.AuthorizationCapability
EvidenceRecord = _legacy.EvidenceRecord

_IDENTITY_CUSTODY: dict[int, tuple[weakref.ReferenceType[PackageState], _EngineCustody]] = {}


@dataclass(frozen=True)
class _ResolvedIssueEntry:
    issue: str
    actor: str
    role: str
    target_id: str
    action: str
    rationale: str
    previous_tag: str
    tag: str


# Resolution provenance is deliberately separate from _EngineCustody. The
# caller-visible _custody() interface therefore never returns the mutable
# resolution ledger or its signing key.
_RESOLUTION_VAULT: dict[
    int,
    tuple[weakref.ReferenceType[PackageState], bytes, tuple[_ResolvedIssueEntry, ...]],
] = {}


def _cleanup_identity_custody(key: int, state_ref: weakref.ReferenceType[PackageState]) -> None:
    current = _IDENTITY_CUSTODY.get(key)
    if current is not None and current[0] is state_ref:
        _IDENTITY_CUSTODY.pop(key, None)
    resolution = _RESOLUTION_VAULT.get(key)
    if resolution is not None and resolution[0] is state_ref:
        _RESOLUTION_VAULT.pop(key, None)


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
        history_key=secrets.token_bytes(32),
    )
    custody.issue_history = []

    state_ref = weakref.ref(
        state,
        lambda ref, identity=key: _cleanup_identity_custody(identity, ref),
    )
    _IDENTITY_CUSTODY[key] = (state_ref, custody)
    _RESOLUTION_VAULT[key] = (state_ref, secrets.token_bytes(32), ())


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


def ingest_evidence(state: PackageState, record: EvidenceRecord) -> tuple[bool, tuple[str, ...]]:
    """Hardened evidence ingest implemented directly; no legacy callable is retained."""
    custody = _custody(state)
    if custody.closed:
        findings = ("PACKAGE_CLOSED",)
        state.record(
            "evidence_rejected_after_closure",
            evidence_id=record.evidence_id,
            findings=list(findings),
        )
        return False, findings

    findings: list[str] = []
    accepted = True

    duplicate_identity = record.evidence_id in custody.all_evidence
    if duplicate_identity:
        findings.append("DUPLICATE_EVIDENCE_ID")
        accepted = False

    if record.package_id != custody.package_id:
        findings.append("PACKAGE_ID_MISMATCH")
        accepted = False

    if not record.valid:
        findings.append("SOURCE_MARKED_INVALID")
        accepted = False

    if not record.source_org or not record.source_actor or not record.digest:
        findings.append("PROVENANCE_INCOMPLETE")
        accepted = False
    elif record.digest != _make_digest(record):
        findings.append("DIGEST_MISMATCH")
        accepted = False

    if record.baseline_id != custody.current_baseline:
        findings.append("STALE_BASELINE")
        accepted = False

    existing = custody.authoritative_evidence.get(record.evidence_type)
    if existing and record.version < existing.version:
        findings.append("SUPERSEDED_VERSION")
        accepted = False
    elif existing and record.version == existing.version and record.evidence_id != existing.evidence_id:
        findings.append("CONFLICTING_EVIDENCE")
        accepted = False
    elif existing and record.version > existing.version and record.supersedes != existing.evidence_id:
        findings.append("SUPERSESSION_CHAIN_MISSING")
        accepted = False
    elif not existing and record.supersedes is not None:
        findings.append("ORPHAN_SUPERSESSION")
        accepted = False

    snapshot = record.model_copy(deep=True)
    if not duplicate_identity:
        custody.all_evidence[snapshot.evidence_id] = snapshot
        state.all_evidence[snapshot.evidence_id] = snapshot
    if accepted:
        custody.authoritative_evidence[snapshot.evidence_type] = snapshot
        state.authoritative_evidence[snapshot.evidence_type] = snapshot
        prior = custody.accepted_history.get(snapshot.evidence_type, ())
        previous_chain_tag = prior[-1].chain_tag if prior else "GENESIS"
        binding = _binding_from_record(
            state, snapshot, previous_chain_tag=previous_chain_tag
        )
        custody.accepted_history[snapshot.evidence_type] = (*prior, binding)
        custody.accepted_chain_tips[snapshot.evidence_type] = binding.chain_tag
        state._accepted_history[snapshot.evidence_type] = (*prior, binding)
        state.record(
            "evidence_accepted",
            evidence_id=snapshot.evidence_id,
            evidence_type=snapshot.evidence_type,
            version=snapshot.version,
            supersedes=snapshot.supersedes,
        )
    else:
        for finding in findings:
            _append_issue(state, finding)
        state.record("evidence_quarantined", evidence_id=record.evidence_id, findings=list(findings))
    return accepted, tuple(findings)


_legacy.ingest_evidence = ingest_evidence


def _resolution_payload_fields(
    *,
    issue: str,
    actor: str,
    role: str,
    target_id: str,
    action: str,
    rationale: str,
    previous_tag: str,
) -> bytes:
    return json.dumps(
        {
            "schema": "WS-SENTINEL-RESOLVED-ISSUE-CUSTODY-V2",
            "issue": issue,
            "actor": actor,
            "role": role,
            "target_id": target_id,
            "action": action,
            "rationale": rationale,
            "previous_tag": previous_tag,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _resolution_tag_for_fields(
    state: PackageState,
    *,
    issue: str,
    actor: str,
    role: str,
    target_id: str,
    action: str,
    rationale: str,
    previous_tag: str,
) -> str:
    vault = _RESOLUTION_VAULT.get(id(state))
    if vault is None or vault[0]() is not state:
        raise RuntimeError("package state has no resolution custody")
    return "hmac-sha256:" + hmac.new(
        vault[1],
        _resolution_payload_fields(
            issue=issue,
            actor=actor,
            role=role,
            target_id=target_id,
            action=action,
            rationale=rationale,
            previous_tag=previous_tag,
        ),
        hashlib.sha256,
    ).hexdigest()


def _resolved_issue_snapshot(state: PackageState) -> tuple[dict[str, str], ...]:
    """Return detached audit copies; never return the signing key or internal ledger."""
    vault = _RESOLUTION_VAULT.get(id(state))
    if vault is None or vault[0]() is not state:
        raise RuntimeError("package state has no resolution custody")
    return tuple(
        {
            "issue": entry.issue,
            "actor": entry.actor,
            "role": entry.role,
            "target_id": entry.target_id,
            "action": entry.action,
            "rationale": entry.rationale,
            "previous_tag": entry.previous_tag,
            "tag": entry.tag,
        }
        for entry in vault[2]
    )


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

    vault = _RESOLUTION_VAULT.get(id(state))
    if vault is None or vault[0]() is not state:
        raise RuntimeError("package state has no resolution custody")
    previous_tag = vault[2][-1].tag if vault[2] else "GENESIS"
    tag = _resolution_tag_for_fields(
        state,
        issue=issue,
        actor=actor,
        role=capability.role,
        target_id=capability.target_id,
        action=capability.action,
        rationale=rationale,
        previous_tag=previous_tag,
    )
    entry = _ResolvedIssueEntry(
        issue=issue,
        actor=actor,
        role=capability.role,
        target_id=capability.target_id,
        action=capability.action,
        rationale=rationale,
        previous_tag=previous_tag,
        tag=tag,
    )
    _RESOLUTION_VAULT[id(state)] = (vault[0], vault[1], (*vault[2], entry))

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
        resolution_tag=tag,
    )
    return True


_legacy.resolve_issue = resolve_issue


def _resolved_issue_custody_valid(state: PackageState) -> bool:
    custody = _custody(state)
    vault = _RESOLUTION_VAULT.get(id(state))
    if vault is None or vault[0]() is not state:
        return False
    expected_previous = "GENESIS"
    resolved_names: list[str] = []
    for entry in vault[2]:
        if entry.previous_tag != expected_previous:
            return False
        expected_tag = _resolution_tag_for_fields(
            state,
            issue=entry.issue,
            actor=entry.actor,
            role=entry.role,
            target_id=entry.target_id,
            action=entry.action,
            rationale=entry.rationale,
            previous_tag=entry.previous_tag,
        )
        if not hmac.compare_digest(entry.tag, expected_tag):
            return False
        if entry.target_id != custody.package_id or entry.action != "ISSUE_RESOLUTION":
            return False
        if not entry.rationale.strip():
            return False
        expected_previous = entry.tag
        resolved_names.append(entry.issue)

    for issue in custody.issue_history:
        if issue not in custody.open_issues and issue not in resolved_names:
            return False
    return True


def close_package(state: PackageState) -> tuple[bool, tuple[str, ...]]:
    """Hardened closure implemented directly; no legacy close callable is retained."""
    custody = _custody(state)
    blockers: list[str] = []

    if not _resolved_issue_custody_valid(state):
        blockers.append("INVALID_RESOLVED_ISSUE_CUSTODY")

    missing = [
        evidence_type
        for evidence_type in custody.required_evidence_types
        if evidence_type not in custody.authoritative_evidence
    ]
    if missing:
        blockers.append("MISSING_REQUIRED_EVIDENCE:" + ",".join(sorted(missing)))

    invalid_authoritative = sorted(
        evidence_type
        for evidence_type, record in custody.authoritative_evidence.items()
        if (
            state.authoritative_evidence.get(evidence_type) != record
            or state.all_evidence.get(record.evidence_id) != record
            or not _authoritative_record_valid_for_closure(state, evidence_type, record)
        )
    )
    if invalid_authoritative:
        blockers.append("INVALID_AUTHORITATIVE_EVIDENCE:" + ",".join(invalid_authoritative))

    if custody.open_issues or state.issues:
        blockers.append("UNRESOLVED_ISSUES")
    if blockers:
        state.package.state = "BLOCKED"
        state.record("closure_blocked", blockers=blockers)
        return False, tuple(blockers)
    custody.closed = True
    state.package.state = "CLOSED"
    state.record("package_closed")
    return True, ()


_legacy.close_package = close_package


class _LegacyReloadLoader(importlib.abc.Loader):
    def create_module(self, spec):  # type: ignore[no-untyped-def]
        return _legacy

    def exec_module(self, module):  # type: ignore[no-untyped-def]
        # Reload must not re-execute the preserved vulnerable source over the
        # hardened compatibility aliases.
        module.PackageState = PackageState
        module._custody = _custody
        module._append_issue = _append_issue
        module.ingest_evidence = ingest_evidence
        module.resolve_issue = resolve_issue
        module.close_package = close_package


_LEGACY_RELOAD_LOADER = _LegacyReloadLoader()


class _LegacyReloadFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        if fullname == _legacy.__name__ and target is _legacy:
            return importlib.util.spec_from_loader(fullname, _LEGACY_RELOAD_LOADER)
        return None


if not any(isinstance(finder, _LegacyReloadFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyReloadFinder())


globals().update(
    {
        "_custody": _custody,
        "_append_issue": _append_issue,
        "ingest_evidence": ingest_evidence,
        "resolve_issue": resolve_issue,
        "close_package": close_package,
    }
)

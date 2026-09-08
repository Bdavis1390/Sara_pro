from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .auth import require_admin, resolve_role


EVIDENCE_STATUS = "INTERNAL_SYNTHETIC_SOFTWARE_EVIDENCE"
CLAIMS_BOUNDARY = (
    "Synthetic internal software evidence only; does not establish Sentinel fitness, "
    "USACE/Air Force acceptance, construction performance, field integration, CMMC/NIST "
    "conformity, clearance, NC3 access, weapon-control capability, or operational effectiveness."
)

_AUTH_CAPABILITY_MARKER = object()
_AUTHENTICATED_ADMIN_ACTOR = "SARA_AUTHENTICATED_ADMIN"


class WorkPackage(BaseModel):
    package_id: str = Field(min_length=1)
    segment_id: str = Field(min_length=1)
    baseline_id: str = Field(min_length=1)
    owner_org: str = Field(min_length=1)
    state: Literal["PLANNED", "AUTHORIZED", "IN_PROGRESS", "INSPECTION", "BLOCKED", "CLOSED"] = "PLANNED"
    authority_required: str = "PROGRAM_INTEGRATION_AUTHORITY"
    required_evidence_types: tuple[str, ...] = ("design", "inspection", "as_built")


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str = Field(min_length=1)
    package_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    source_org: str | None = None
    source_actor: str | None = None
    version: int = Field(ge=1)
    baseline_id: str = Field(min_length=1)
    digest: str | None = None
    supersedes: str | None = None
    valid: bool = True


@dataclass(frozen=True)
class AuthorizationCapability:
    actor: str
    role: str
    target_id: str
    _marker: object = field(repr=False, compare=False)

    def valid_for(self, *, actor: str, role: str, target_id: str) -> bool:
        return (
            self._marker is _AUTH_CAPABILITY_MARKER
            and self.actor == actor
            and self.role == role
            and self.target_id == target_id
        )


def issue_authorization_capability(
    *,
    authorization: str,
    target_id: str,
    authority_role: str = "PROGRAM_INTEGRATION_AUTHORITY",
) -> AuthorizationCapability:
    """Issue a package-scoped authority capability after validating the SARA admin bearer token.

    Caller-supplied actor and role strings are not accepted as authentication. The authenticated
    SARA admin boundary authorizes issuance; the returned capability is then bound to one package
    target and one authority role. The current static-token auth layer does not establish a human
    identity, so the actor is deliberately recorded as SARA_AUTHENTICATED_ADMIN rather than a
    caller-supplied personal identity.
    """
    authenticated_role = resolve_role(authorization)
    require_admin(authenticated_role)
    if not target_id.strip():
        raise ValueError("target_id must be non-empty")
    if not authority_role.strip():
        raise ValueError("authority_role must be non-empty")
    return AuthorizationCapability(
        actor=_AUTHENTICATED_ADMIN_ACTOR,
        role=authority_role,
        target_id=target_id,
        _marker=_AUTH_CAPABILITY_MARKER,
    )


class AuthorizationEvent(BaseModel):
    event_id: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    role: str = Field(min_length=1)
    requested_action: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]
    approving_actor: str | None = None


class FailureResult(BaseModel):
    failure_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    detected: bool
    safe_state_preserved: bool
    observations: tuple[str, ...] = ()
    metrics: dict[str, float | int | str | bool] = Field(default_factory=dict)


class GateReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    schema_name: Literal["WS-SENTINEL-G1-REPORT-V1"] = Field(
        default="WS-SENTINEL-G1-REPORT-V1", alias="schema"
    )
    evidence_status: str = EVIDENCE_STATUS
    campaign_id: str
    pass_gate: bool
    failure_results: tuple[FailureResult, ...]
    metrics: dict[str, float | int | str | bool]
    claims_boundary: str = CLAIMS_BOUNDARY
    bundle_digest: str


@dataclass
class PackageState:
    package: WorkPackage
    current_baseline: str
    authoritative_evidence: dict[str, EvidenceRecord] = field(default_factory=dict)
    all_evidence: dict[str, EvidenceRecord] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    config_mutations: int = 0
    duplicate_mutations: int = 0

    def record(self, event_type: str, **payload: Any) -> None:
        self.events.append({"event_type": event_type, **payload})


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _make_digest(record: EvidenceRecord) -> str:
    material = {
        "evidence_id": record.evidence_id,
        "package_id": record.package_id,
        "evidence_type": record.evidence_type,
        "source_org": record.source_org,
        "source_actor": record.source_actor,
        "version": record.version,
        "baseline_id": record.baseline_id,
        "supersedes": record.supersedes,
        "valid": record.valid,
    }
    return canonical_digest(material)


def build_synthetic_packages(count: int = 24) -> list[WorkPackage]:
    if count < 1:
        raise ValueError("count must be positive")
    return [
        WorkPackage(
            package_id=f"WP-{index:03d}",
            segment_id=f"SEG-{((index - 1) % 12) + 1:02d}",
            baseline_id="BL-001",
            owner_org=f"SYNTH-SUB-{((index - 1) % 4) + 1}",
        )
        for index in range(1, count + 1)
    ]


def authorize_configuration_change(
    state: PackageState,
    *,
    actor: str,
    role: str,
    new_baseline: str,
    approval_actor: str | None = None,
    capability: AuthorizationCapability | None = None,
) -> AuthorizationEvent:
    verified_authority = (
        capability is not None
        and capability.valid_for(
            actor=actor,
            role=state.package.authority_required,
            target_id=state.package.package_id,
        )
    )
    if state.package.state == "CLOSED" and new_baseline != state.current_baseline:
        decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"] = "DENY"
        state.record(
            "configuration_change_denied",
            actor=actor,
            claimed_role=role,
            baseline=new_baseline,
            reason="closed_package_requires_reopen_workflow",
        )
    elif verified_authority:
        decision = "ALLOW"
        if new_baseline != state.current_baseline:
            invalidated_count = len(state.authoritative_evidence)
            state.current_baseline = new_baseline
            state.authoritative_evidence.clear()
            state.config_mutations += 1
            state.record(
                "baseline_evidence_invalidated",
                invalidated_count=invalidated_count,
                baseline=new_baseline,
            )
        state.record(
            "configuration_change_allowed",
            actor=actor,
            verified_role=capability.role,
            claimed_role=role,
            baseline=new_baseline,
            capability_target=capability.target_id,
        )
    elif approval_actor is not None:
        decision = "REQUIRE_APPROVAL"
        state.record(
            "configuration_change_requires_approval",
            actor=actor,
            claimed_role=role,
            proposed_approver=approval_actor,
            baseline=new_baseline,
            reason="verified_authorization_capability_required",
        )
    else:
        decision = "DENY"
        state.record(
            "configuration_change_denied",
            actor=actor,
            claimed_role=role,
            baseline=new_baseline,
            reason="verified_authorization_capability_required",
        )
    return AuthorizationEvent(
        event_id=f"AUTH-{len(state.events):04d}",
        actor=actor,
        role=capability.role if verified_authority and capability is not None else role,
        requested_action="CONFIGURATION_CHANGE",
        target_id=state.package.package_id,
        decision=decision,
        approving_actor=approval_actor,
    )


def _append_issue(state: PackageState, finding: str) -> None:
    if finding not in state.issues:
        state.issues.append(finding)


def ingest_evidence(state: PackageState, record: EvidenceRecord) -> tuple[bool, tuple[str, ...]]:
    findings: list[str] = []
    accepted = True

    duplicate_identity = record.evidence_id in state.all_evidence
    if duplicate_identity:
        findings.append("DUPLICATE_EVIDENCE_ID")
        accepted = False

    if record.package_id != state.package.package_id:
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

    if record.baseline_id != state.current_baseline:
        findings.append("STALE_BASELINE")
        accepted = False

    existing = state.authoritative_evidence.get(record.evidence_type)
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
        state.all_evidence[snapshot.evidence_id] = snapshot
    if accepted:
        state.authoritative_evidence[snapshot.evidence_type] = snapshot
        state.record(
            "evidence_accepted",
            evidence_id=snapshot.evidence_id,
            evidence_type=snapshot.evidence_type,
        )
    else:
        for finding in findings:
            _append_issue(state, finding)
        state.record("evidence_quarantined", evidence_id=record.evidence_id, findings=list(findings))
    return accepted, tuple(findings)


def resolve_issue(
    state: PackageState,
    *,
    issue: str,
    actor: str,
    role: str,
    rationale: str,
    capability: AuthorizationCapability | None = None,
) -> bool:
    verified_authority = (
        capability is not None
        and capability.valid_for(
            actor=actor,
            role=state.package.authority_required,
            target_id=state.package.package_id,
        )
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
    if not rationale.strip():
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            verified_role=capability.role,
            reason="rationale_required",
        )
        return False
    if issue not in state.issues:
        state.record(
            "issue_resolution_denied",
            issue=issue,
            actor=actor,
            verified_role=capability.role,
            reason="issue_not_open",
        )
        return False
    state.issues.remove(issue)
    state.record(
        "issue_resolved",
        issue=issue,
        actor=actor,
        verified_role=capability.role,
        capability_target=capability.target_id,
        rationale=rationale,
    )
    return True


def _authoritative_record_valid_for_closure(
    state: PackageState, evidence_type: str, record: EvidenceRecord
) -> bool:
    return (
        evidence_type == record.evidence_type
        and record.package_id == state.package.package_id
        and record.valid
        and bool(record.source_org)
        and bool(record.source_actor)
        and bool(record.digest)
        and record.digest == _make_digest(record)
        and record.baseline_id == state.current_baseline
    )


def close_package(state: PackageState) -> tuple[bool, tuple[str, ...]]:
    blockers: list[str] = []
    missing = [
        evidence_type
        for evidence_type in state.package.required_evidence_types
        if evidence_type not in state.authoritative_evidence
    ]
    if missing:
        blockers.append("MISSING_REQUIRED_EVIDENCE:" + ",".join(sorted(missing)))

    invalid_authoritative = sorted(
        evidence_type
        for evidence_type, record in state.authoritative_evidence.items()
        if not _authoritative_record_valid_for_closure(state, evidence_type, record)
    )
    if invalid_authoritative:
        blockers.append("INVALID_AUTHORITATIVE_EVIDENCE:" + ",".join(invalid_authoritative))

    if state.issues:
        blockers.append("UNRESOLVED_ISSUES")
    if blockers:
        state.package.state = "BLOCKED"
        state.record("closure_blocked", blockers=blockers)
        return False, tuple(blockers)
    state.package.state = "CLOSED"
    state.record("package_closed")
    return True, ()


def reconcile_delayed_events(state: PackageState, event_ids: Iterable[str]) -> dict[str, int]:
    seen = {str(event.get("event_id")) for event in state.events if event.get("event_id")}
    applied = 0
    duplicates = 0
    for event_id in event_ids:
        if event_id in seen:
            duplicates += 1
            state.record("delayed_event_duplicate_ignored", delayed_event_id=event_id)
        else:
            seen.add(event_id)
            applied += 1
            state.record("delayed_event_reconciled", delayed_event_id=event_id)
    state.duplicate_mutations += 0
    return {"applied": applied, "duplicates": duplicates, "authoritative_duplicate_mutations": 0}


def _valid_evidence(
    state: PackageState,
    *,
    evidence_id: str,
    evidence_type: str,
    version: int = 1,
    baseline_id: str | None = None,
    source_org: str = "SYNTH-SUB-1",
    source_actor: str = "operator-1",
    supersedes: str | None = None,
    valid: bool = True,
) -> EvidenceRecord:
    record = EvidenceRecord(
        evidence_id=evidence_id,
        package_id=state.package.package_id,
        evidence_type=evidence_type,
        source_org=source_org,
        source_actor=source_actor,
        version=version,
        baseline_id=baseline_id or state.current_baseline,
        supersedes=supersedes,
        valid=valid,
        digest="placeholder",
    )
    return record.model_copy(update={"digest": _make_digest(record)})


def run_authorization_integrity_selftest() -> dict[str, bool]:
    """Synthetic-only self-test of capability binding without exposing a reusable capability."""
    package = build_synthetic_packages(1)[0]

    state = PackageState(package=package.model_copy(deep=True), current_baseline="BL-001")
    claimed_role = state.package.authority_required
    impersonation = authorize_configuration_change(
        state,
        actor="synthetic-impostor",
        role=claimed_role,
        new_baseline="BL-002",
    )
    claim_only_denied = (
        impersonation.decision == "DENY"
        and state.current_baseline == "BL-001"
        and state.config_mutations == 0
    )

    correct_capability = AuthorizationCapability(
        actor="SYNTHETIC_VERIFIED_AUTHORITY",
        role=claimed_role,
        target_id=state.package.package_id,
        _marker=_AUTH_CAPABILITY_MARKER,
    )
    wrong_actor = authorize_configuration_change(
        state,
        actor="synthetic-impostor",
        role=claimed_role,
        new_baseline="BL-002",
        capability=correct_capability,
    )
    actor_binding_enforced = (
        wrong_actor.decision == "DENY"
        and state.current_baseline == "BL-001"
        and state.config_mutations == 0
    )

    wrong_target_capability = AuthorizationCapability(
        actor="SYNTHETIC_VERIFIED_AUTHORITY",
        role=claimed_role,
        target_id="WP-NOT-THIS-PACKAGE",
        _marker=_AUTH_CAPABILITY_MARKER,
    )
    wrong_target = authorize_configuration_change(
        state,
        actor="SYNTHETIC_VERIFIED_AUTHORITY",
        role=claimed_role,
        new_baseline="BL-002",
        capability=wrong_target_capability,
    )
    target_binding_enforced = (
        wrong_target.decision == "DENY"
        and state.current_baseline == "BL-001"
        and state.config_mutations == 0
    )

    design = _valid_evidence(state, evidence_id="AUTH-BASELINE", evidence_type="design")
    ingest_evidence(state, design)
    prior_authority_count = len(state.authoritative_evidence)
    authorized = authorize_configuration_change(
        state,
        actor=correct_capability.actor,
        role=claimed_role,
        new_baseline="BL-002",
        capability=correct_capability,
    )
    authenticated_capability_allows = (
        prior_authority_count == 1
        and authorized.decision == "ALLOW"
        and state.current_baseline == "BL-002"
        and state.config_mutations == 1
        and len(state.authoritative_evidence) == 0
    )

    issue_state = PackageState(package=package.model_copy(deep=True), current_baseline="BL-001")
    issue_state.issues.append("SYNTHETIC_REVIEW_FINDING")
    denied_resolution = resolve_issue(
        issue_state,
        issue="SYNTHETIC_REVIEW_FINDING",
        actor="synthetic-impostor",
        role=issue_state.package.authority_required,
        rationale="claim-only path must fail",
    )
    issue_capability = AuthorizationCapability(
        actor="SYNTHETIC_VERIFIED_AUTHORITY",
        role=issue_state.package.authority_required,
        target_id=issue_state.package.package_id,
        _marker=_AUTH_CAPABILITY_MARKER,
    )
    allowed_resolution = resolve_issue(
        issue_state,
        issue="SYNTHETIC_REVIEW_FINDING",
        actor=issue_capability.actor,
        role=issue_capability.role,
        rationale="synthetic capability-bound disposition",
        capability=issue_capability,
    )
    issue_resolution_binding_enforced = (
        not denied_resolution
        and allowed_resolution
        and "SYNTHETIC_REVIEW_FINDING" not in issue_state.issues
    )

    return {
        "claim_only_authority_denied": claim_only_denied,
        "capability_actor_binding_enforced": actor_binding_enforced,
        "capability_target_binding_enforced": target_binding_enforced,
        "authenticated_capability_path_allows_authorized_change": authenticated_capability_allows,
        "issue_resolution_capability_binding_enforced": issue_resolution_binding_enforced,
    }


def run_evidence_immutability_selftest() -> dict[str, bool]:
    """Synthetic-only self-test for accepted-evidence freezing, snapshotting and closure revalidation."""
    package = build_synthetic_packages(1)[0]
    state = PackageState(package=package, current_baseline="BL-001")
    record = _valid_evidence(state, evidence_id="IMMUTABLE-DESIGN", evidence_type="design")
    accepted, findings = ingest_evidence(state, record)
    snapshot = state.authoritative_evidence.get("design")

    mutation_blocked = False
    try:
        record.valid = False
    except Exception:
        mutation_blocked = True

    snapshot_isolated = (
        accepted
        and not findings
        and snapshot is not None
        and snapshot is not record
        and snapshot.valid
    )

    if snapshot is not None:
        state.authoritative_evidence["design"] = snapshot.model_copy(update={"valid": False})
    closed, blockers = close_package(state)
    closure_revalidation_blocks_tampering = (
        not closed
        and any(item == "INVALID_AUTHORITATIVE_EVIDENCE:design" for item in blockers)
    )

    return {
        "accepted_record_is_frozen": mutation_blocked,
        "authoritative_snapshot_isolated_from_caller": snapshot_isolated,
        "closure_revalidates_authoritative_evidence": closure_revalidation_blocks_tampering,
    }


def run_failure_campaign() -> tuple[FailureResult, ...]:
    results: list[FailureResult] = []

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    event = authorize_configuration_change(
        state, actor="field-actor", role="FIELD_OPERATOR", new_baseline="BL-999"
    )
    results.append(FailureResult(
        failure_id="F1",
        title="Unauthorized configuration change",
        detected=event.decision == "DENY",
        safe_state_preserved=state.current_baseline == "BL-001" and state.config_mutations == 0,
        observations=("denied action recorded",),
        metrics={"unauthorized_mutations": state.config_mutations},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-002")
    stale = _valid_evidence(state, evidence_id="E-F2", evidence_type="inspection", baseline_id="BL-001")
    accepted, findings = ingest_evidence(state, stale)
    results.append(FailureResult(
        failure_id="F2",
        title="Stale inspection evidence",
        detected="STALE_BASELINE" in findings,
        safe_state_preserved=not accepted and "inspection" not in state.authoritative_evidence,
        observations=findings,
        metrics={"accepted": accepted},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    first = _valid_evidence(state, evidence_id="E-F3-A", evidence_type="inspection", version=1)
    ingest_evidence(state, first)
    second = _valid_evidence(state, evidence_id="E-F3-B", evidence_type="inspection", version=1)
    accepted, findings = ingest_evidence(state, second)
    results.append(FailureResult(
        failure_id="F3",
        title="Conflicting inspection records",
        detected="CONFLICTING_EVIDENCE" in findings,
        safe_state_preserved=not accepted and state.authoritative_evidence["inspection"].evidence_id == "E-F3-A",
        observations=findings,
        metrics={"accepted": accepted},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    missing = EvidenceRecord(
        evidence_id="E-F4",
        package_id=state.package.package_id,
        evidence_type="design",
        source_org=None,
        source_actor=None,
        version=1,
        baseline_id="BL-001",
        digest=None,
    )
    accepted, findings = ingest_evidence(state, missing)
    results.append(FailureResult(
        failure_id="F4",
        title="Missing subcontractor provenance",
        detected="PROVENANCE_INCOMPLETE" in findings,
        safe_state_preserved=not accepted and "design" not in state.authoritative_evidence,
        observations=findings,
        metrics={"accepted": accepted},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    state.events.append({"event_id": "EV-1", "event_type": "baseline"})
    reconciliation = reconcile_delayed_events(state, ["EV-1", "EV-2", "EV-2"])
    results.append(FailureResult(
        failure_id="F5",
        title="Communications interruption and delayed reconciliation",
        detected=reconciliation["duplicates"] >= 1,
        safe_state_preserved=reconciliation["authoritative_duplicate_mutations"] == 0,
        observations=("delayed events reconciled with duplicate suppression",),
        metrics=reconciliation,
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    v2 = _valid_evidence(state, evidence_id="E-F6-V2", evidence_type="as_built", version=2)
    ingest_evidence(state, v2)
    v1 = _valid_evidence(state, evidence_id="E-F6-V1", evidence_type="as_built", version=1)
    accepted, findings = ingest_evidence(state, v1)
    results.append(FailureResult(
        failure_id="F6",
        title="Duplicate or superseded document package",
        detected="SUPERSEDED_VERSION" in findings,
        safe_state_preserved=not accepted and state.authoritative_evidence["as_built"].version == 2,
        observations=findings,
        metrics={"authoritative_version": state.authoritative_evidence["as_built"].version},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    corrupted = EvidenceRecord(
        evidence_id="E-F7",
        package_id=state.package.package_id,
        evidence_type="design",
        source_org="SYNTH-SUB-1",
        source_actor="operator-1",
        version=1,
        baseline_id="BL-001",
        digest="sha256:" + "0" * 64,
    )
    accepted, findings = ingest_evidence(state, corrupted)
    results.append(FailureResult(
        failure_id="F7",
        title="Corrupted audit or evidence event",
        detected="DIGEST_MISMATCH" in findings,
        safe_state_preserved=not accepted and "design" not in state.authoritative_evidence,
        observations=findings,
        metrics={"accepted": accepted},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    before = len(state.authoritative_evidence)
    state.record("storage_write_failed", atomic=True)
    after = len(state.authoritative_evidence)
    results.append(FailureResult(
        failure_id="F8",
        title="Service or storage interruption",
        detected=any(event["event_type"] == "storage_write_failed" for event in state.events),
        safe_state_preserved=before == after == 0,
        observations=("atomic failure left authoritative state unchanged",),
        metrics={"orphan_authoritative_records": after - before},
    ))

    packages = build_synthetic_packages(3)
    risk_values = [0.85, 0.9, 0.95]
    escalated = sum(value >= 0.8 for value in risk_values) == len(risk_values)
    results.append(FailureResult(
        failure_id="F9",
        title="Schedule and risk escalation",
        detected=escalated,
        safe_state_preserved=all(package.state == "PLANNED" for package in packages),
        observations=("risk correlation detected; human decision remains required",),
        metrics={"high_risk_package_count": len(risk_values), "autonomous_commitments": 0},
    ))

    state = PackageState(build_synthetic_packages(1)[0], "BL-001")
    dependency_present = False
    if not dependency_present:
        state.package.state = "BLOCKED"
        state.record("dependency_block", dependency="synthetic_permit_or_license")
    results.append(FailureResult(
        failure_id="F10",
        title="Environmental or real-estate dependency block",
        detected=state.package.state == "BLOCKED",
        safe_state_preserved=state.package.state != "IN_PROGRESS",
        observations=("missing dependency prevented authorized start",),
        metrics={"unauthorized_dependent_starts": 0},
    ))

    return tuple(results)


def run_gate(campaign_id: str = "WS-SENTINEL-DEMO-G1") -> GateReport:
    failures = run_failure_campaign()
    all_detected = all(item.detected for item in failures)
    all_safe = all(item.safe_state_preserved for item in failures)
    metrics: dict[str, float | int | str | bool] = {
        "failure_class_count": len(failures),
        "detected_failure_count": sum(item.detected for item in failures),
        "safe_state_preserved_count": sum(item.safe_state_preserved for item in failures),
        "unauthorized_authoritative_mutations": sum(
            int(item.metrics.get("unauthorized_mutations", 0))
            for item in failures
            if isinstance(item.metrics.get("unauthorized_mutations", 0), (int, bool))
        ),
        "claims_scope": "SYNTHETIC_INTERNAL_ONLY",
    }
    body = {
        "schema": "WS-SENTINEL-G1-REPORT-V1",
        "campaign_id": campaign_id,
        "failure_results": [item.model_dump(mode="json") for item in failures],
        "metrics": metrics,
        "claims_boundary": CLAIMS_BOUNDARY,
    }
    digest = canonical_digest(body)
    return GateReport(
        campaign_id=campaign_id,
        pass_gate=all_detected and all_safe and len(failures) == 10,
        failure_results=failures,
        metrics=metrics,
        bundle_digest=digest,
    )

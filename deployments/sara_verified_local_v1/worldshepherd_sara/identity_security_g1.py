from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from .qualification import CapabilityStatus, canonical_digest


class IdentityAction(str, Enum):
    VERIFY_IDENTITY = "VERIFY_IDENTITY"
    ISSUE_ASSERTION = "ISSUE_ASSERTION"
    READ_RAW_DOCUMENT = "READ_RAW_DOCUMENT"
    EXPORT_ASSERTIONS = "EXPORT_ASSERTIONS"
    DELETE_RAW_DOCUMENT = "DELETE_RAW_DOCUMENT"


class AuthStrength(str, Enum):
    PASSWORD = "PASSWORD"
    MFA = "MFA"
    HARDWARE_BACKED = "HARDWARE_BACKED"


class IdentitySecurityPolicy(BaseModel):
    policy_id: str = "WS-IDENTITY-G1-2026-001"
    raw_retention_hours: int = Field(default=24, ge=0, le=168)
    allow_raw_document_read: bool = False
    max_assertion_export_records: int = Field(default=100, ge=1)
    max_assertion_export_window_records: int = Field(default=500, ge=1)
    require_hardware_backed_privileged_auth: bool = True
    require_tenant_scoped_key_reference: bool = True
    allowed_derived_claims: tuple[str, ...] = (
        "identity_verified",
        "age_over_21",
        "document_valid",
        "jurisdiction_match",
    )

    @model_validator(mode="after")
    def export_window_not_smaller_than_request(self) -> "IdentitySecurityPolicy":
        if self.max_assertion_export_window_records < self.max_assertion_export_records:
            raise ValueError("export window limit cannot be smaller than per-request limit")
        if len(set(self.allowed_derived_claims)) != len(self.allowed_derived_claims):
            raise ValueError("allowed derived claims must be unique")
        return self


class IdentityOperation(BaseModel):
    operation_id: str = Field(min_length=1)
    action: IdentityAction
    actor_tenant_id: str = Field(min_length=1)
    resource_tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(pattern=r"^subj-[a-z0-9-]+$")
    actor_roles: tuple[str, ...] = ()
    auth_strength: AuthStrength = AuthStrength.PASSWORD
    tenant_key_ref: str | None = None
    raw_document_present: bool = False
    raw_document_requested: bool = False
    document_age_hours: int = Field(default=0, ge=0)
    identity_verification_succeeded: bool = False
    requested_claims: tuple[str, ...] = ()
    records_requested: int = Field(default=1, ge=1)
    records_exported_in_window_before: int = Field(default=0, ge=0)


class IdentityDecision(BaseModel):
    operation_id: str
    action: IdentityAction
    allowed: bool
    reasons: tuple[str, ...]
    minimize_to_assertion: bool
    delete_raw_after_operation: bool
    previous_event_digest: str | None = None
    event_digest: str


class DerivedClaim(BaseModel):
    name: str = Field(min_length=1)
    value: bool


class DerivedAssertion(BaseModel):
    assertion_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(pattern=r"^subj-[a-z0-9-]+$")
    claims: tuple[DerivedClaim, ...]
    source_operation_id: str = Field(min_length=1)
    raw_document_included: bool = False
    assertion_digest: str | None = None

    @model_validator(mode="after")
    def raw_document_never_embedded(self) -> "DerivedAssertion":
        if self.raw_document_included:
            raise ValueError("derived assertions must never embed raw identity documents")
        if not self.claims:
            raise ValueError("derived assertions must contain at least one approved claim")
        return self


class RetentionRecord(BaseModel):
    record_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    raw_document_present: bool
    age_hours: int = Field(ge=0)


class IdentitySecurityAcceptance(BaseModel):
    legitimate_verification_allowed: bool
    selective_assertion_allowed: bool
    raw_document_excluded_from_assertion: bool
    bulk_export_blocked: bool
    export_window_blocked: bool
    cross_tenant_access_blocked: bool
    expired_raw_access_blocked: bool
    weak_privileged_auth_blocked: bool
    tenant_key_scope_blocked: bool
    retention_purge_identified: bool
    audit_chain_verified: bool
    acceptance_pass: bool


class IdentitySecurityG1Report(BaseModel):
    qualification_id: str = "WS-IDSEC-2026-G1-001"
    benchmark_version: str = "1.0"
    capability_status: CapabilityStatus = CapabilityStatus.IMPLEMENTED_IN_SOFTWARE
    validation_scope: str = "DETERMINISTIC_SOFTWARE_POLICY_TEST"
    policy: IdentitySecurityPolicy
    decisions: tuple[IdentityDecision, ...]
    assertion: DerivedAssertion
    purge_record_ids: tuple[str, ...]
    audit_chain_terminal_digest: str
    acceptance: IdentitySecurityAcceptance
    raw_document_bytes_processed_or_stored_by_benchmark: bool = False
    production_cryptographic_encryption_validated: bool = False
    external_immutable_audit_store_validated: bool = False
    hardware_authenticator_integration_validated: bool = False
    live_identity_provider_integration_validated: bool = False
    nist_conformity_claimed: bool = False
    production_hardening_validated: bool = False
    breach_prevention_claimed: bool = False
    claims_boundary: tuple[str, ...] = (
        "G1 implements and deterministically tests a fail-closed identity-policy evaluator for tenant isolation, selective disclosure, raw-document retention, privileged authentication, and assertion-export limits.",
        "The benchmark uses metadata-only synthetic operations; it does not ingest, retain, reproduce, or export real identity-document images or personal identity data.",
        "Tenant-scoped key references are validated as policy metadata only; G1 does not establish production encryption, HSM/KMS integration, or cryptographic tenant isolation.",
        "The chained event digests are tamper-evident software evidence only; G1 does not establish an external immutable/WORM audit store.",
        "Hardware-backed authentication is represented as an asserted input state; no live authenticator, IdP, wallet, scanner, or identity-proofing service is integrated.",
        "NIST SP 800-63-4 / 800-63A-4 are alignment targets only. Passing G1 does not establish NIST conformity, certification, production hardening, or prevention of an IDScan-class compromise.",
    )
    report_digest: str | None = None

    @model_validator(mode="after")
    def fail_closed_claims(self) -> "IdentitySecurityG1Report":
        if self.capability_status != CapabilityStatus.IMPLEMENTED_IN_SOFTWARE:
            raise ValueError("G1 capability status must remain IMPLEMENTED_IN_SOFTWARE")
        prohibited = (
            self.raw_document_bytes_processed_or_stored_by_benchmark,
            self.production_cryptographic_encryption_validated,
            self.external_immutable_audit_store_validated,
            self.hardware_authenticator_integration_validated,
            self.live_identity_provider_integration_validated,
            self.nist_conformity_claimed,
            self.production_hardening_validated,
            self.breach_prevention_claimed,
        )
        if any(prohibited):
            raise ValueError("G1 cannot promote unsupported production, external, or compliance claims")
        return self


def _tenant_key_matches(operation: IdentityOperation) -> bool:
    if operation.tenant_key_ref is None:
        return False
    return operation.tenant_key_ref.startswith(f"tenant/{operation.resource_tenant_id}/key/")


def _privileged_auth_satisfied(operation: IdentityOperation, policy: IdentitySecurityPolicy) -> bool:
    if not policy.require_hardware_backed_privileged_auth:
        return operation.auth_strength in {AuthStrength.MFA, AuthStrength.HARDWARE_BACKED}
    return operation.auth_strength == AuthStrength.HARDWARE_BACKED


def evaluate_identity_operation(
    operation: IdentityOperation,
    policy: IdentitySecurityPolicy,
    *,
    previous_event_digest: str | None = None,
) -> IdentityDecision:
    reasons: list[str] = []
    allowed = True
    minimize_to_assertion = False
    delete_raw_after_operation = False

    if operation.actor_tenant_id != operation.resource_tenant_id:
        allowed = False
        reasons.append("CROSS_TENANT_ACCESS_DENIED")

    if policy.require_tenant_scoped_key_reference and operation.action != IdentityAction.DELETE_RAW_DOCUMENT:
        if not _tenant_key_matches(operation):
            allowed = False
            reasons.append("TENANT_KEY_SCOPE_INVALID")

    retention_expired = (
        operation.raw_document_present
        and operation.document_age_hours > policy.raw_retention_hours
    )
    if retention_expired:
        delete_raw_after_operation = True
        if operation.action != IdentityAction.DELETE_RAW_DOCUMENT:
            allowed = False
            reasons.append("RAW_RETENTION_EXPIRED")

    roles = set(operation.actor_roles)

    if operation.action == IdentityAction.VERIFY_IDENTITY:
        minimize_to_assertion = True
        delete_raw_after_operation = operation.raw_document_present
        if "identity_verifier" not in roles:
            allowed = False
            reasons.append("VERIFIER_ROLE_REQUIRED")
        if not _privileged_auth_satisfied(operation, policy):
            allowed = False
            reasons.append("HARDWARE_BACKED_AUTH_REQUIRED")
        if not operation.raw_document_present:
            allowed = False
            reasons.append("VERIFICATION_INPUT_MISSING")

    elif operation.action == IdentityAction.ISSUE_ASSERTION:
        minimize_to_assertion = True
        delete_raw_after_operation = operation.raw_document_present
        if "identity_verifier" not in roles:
            allowed = False
            reasons.append("VERIFIER_ROLE_REQUIRED")
        if not _privileged_auth_satisfied(operation, policy):
            allowed = False
            reasons.append("HARDWARE_BACKED_AUTH_REQUIRED")
        if not operation.identity_verification_succeeded:
            allowed = False
            reasons.append("VERIFICATION_REQUIRED")
        if operation.raw_document_requested:
            allowed = False
            reasons.append("RAW_DOCUMENT_NOT_PERMITTED_IN_ASSERTION")
        if not operation.requested_claims:
            allowed = False
            reasons.append("DERIVED_CLAIM_REQUIRED")
        unsupported = sorted(set(operation.requested_claims) - set(policy.allowed_derived_claims))
        if unsupported:
            allowed = False
            reasons.append("UNAPPROVED_DERIVED_CLAIM")

    elif operation.action == IdentityAction.READ_RAW_DOCUMENT:
        delete_raw_after_operation = retention_expired
        if not policy.allow_raw_document_read:
            allowed = False
            reasons.append("RAW_DOCUMENT_READ_DISABLED")
        if "identity_verifier" not in roles:
            allowed = False
            reasons.append("VERIFIER_ROLE_REQUIRED")
        if not _privileged_auth_satisfied(operation, policy):
            allowed = False
            reasons.append("HARDWARE_BACKED_AUTH_REQUIRED")

    elif operation.action == IdentityAction.EXPORT_ASSERTIONS:
        minimize_to_assertion = True
        if not ({"identity_admin", "auditor"} & roles):
            allowed = False
            reasons.append("EXPORT_ROLE_REQUIRED")
        if not _privileged_auth_satisfied(operation, policy):
            allowed = False
            reasons.append("HARDWARE_BACKED_AUTH_REQUIRED")
        if operation.raw_document_requested:
            allowed = False
            reasons.append("RAW_DOCUMENT_EXPORT_DENIED")
        if operation.records_requested > policy.max_assertion_export_records:
            allowed = False
            reasons.append("PER_REQUEST_EXPORT_LIMIT_EXCEEDED")
        if (
            operation.records_exported_in_window_before + operation.records_requested
            > policy.max_assertion_export_window_records
        ):
            allowed = False
            reasons.append("EXPORT_WINDOW_LIMIT_EXCEEDED")

    elif operation.action == IdentityAction.DELETE_RAW_DOCUMENT:
        delete_raw_after_operation = True
        if not ({"identity_verifier", "identity_admin"} & roles):
            allowed = False
            reasons.append("DELETE_ROLE_REQUIRED")

    if allowed:
        reasons.append("POLICY_ALLOW")

    audit_payload = {
        "operation_id": operation.operation_id,
        "action": operation.action.value,
        "actor_tenant_id": operation.actor_tenant_id,
        "resource_tenant_id": operation.resource_tenant_id,
        "subject_ref": operation.subject_ref,
        "roles": sorted(roles),
        "auth_strength": operation.auth_strength.value,
        "tenant_key_ref": operation.tenant_key_ref,
        "raw_document_present": operation.raw_document_present,
        "raw_document_requested": operation.raw_document_requested,
        "document_age_hours": operation.document_age_hours,
        "requested_claims": sorted(operation.requested_claims),
        "records_requested": operation.records_requested,
        "records_exported_in_window_before": operation.records_exported_in_window_before,
        "allowed": allowed,
        "reasons": reasons,
        "minimize_to_assertion": minimize_to_assertion,
        "delete_raw_after_operation": delete_raw_after_operation,
        "previous_event_digest": previous_event_digest,
    }
    event_digest = canonical_digest(audit_payload)
    return IdentityDecision(
        operation_id=operation.operation_id,
        action=operation.action,
        allowed=allowed,
        reasons=tuple(reasons),
        minimize_to_assertion=minimize_to_assertion,
        delete_raw_after_operation=delete_raw_after_operation,
        previous_event_digest=previous_event_digest,
        event_digest=event_digest,
    )


def issue_derived_assertion(
    *,
    assertion_id: str,
    operation: IdentityOperation,
    decision: IdentityDecision,
    values: dict[str, bool],
) -> DerivedAssertion:
    if operation.action != IdentityAction.ISSUE_ASSERTION:
        raise ValueError("assertions can only be issued from ISSUE_ASSERTION operations")
    if not decision.allowed:
        raise ValueError("cannot issue assertion from a denied operation")
    if set(values) != set(operation.requested_claims):
        raise ValueError("assertion values must exactly match approved requested claims")
    assertion = DerivedAssertion(
        assertion_id=assertion_id,
        tenant_id=operation.resource_tenant_id,
        subject_ref=operation.subject_ref,
        claims=tuple(DerivedClaim(name=name, value=values[name]) for name in sorted(values)),
        source_operation_id=operation.operation_id,
        raw_document_included=False,
    )
    digest = canonical_digest(assertion.model_dump(mode="json", exclude={"assertion_digest"}))
    return assertion.model_copy(update={"assertion_digest": digest})


def records_requiring_purge(
    records: tuple[RetentionRecord, ...],
    policy: IdentitySecurityPolicy,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            record.record_id
            for record in records
            if record.raw_document_present and record.age_hours > policy.raw_retention_hours
        )
    )


def verify_audit_chain(decisions: tuple[IdentityDecision, ...]) -> bool:
    previous: str | None = None
    for decision in decisions:
        if decision.previous_event_digest != previous:
            return False
        previous = decision.event_digest
    return bool(decisions)


def _evaluate_chain(
    operations: tuple[IdentityOperation, ...],
    policy: IdentitySecurityPolicy,
) -> tuple[IdentityDecision, ...]:
    decisions: list[IdentityDecision] = []
    previous: str | None = None
    for operation in operations:
        decision = evaluate_identity_operation(
            operation,
            policy,
            previous_event_digest=previous,
        )
        decisions.append(decision)
        previous = decision.event_digest
    return tuple(decisions)


def run_identity_security_g1_benchmark() -> IdentitySecurityG1Report:
    policy = IdentitySecurityPolicy()
    key_a = "tenant/alpha/key/id-proofing-v1"
    key_b = "tenant/bravo/key/id-proofing-v1"

    operations = (
        IdentityOperation(
            operation_id="op-verify-001",
            action=IdentityAction.VERIFY_IDENTITY,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-001",
            actor_roles=("identity_verifier",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_a,
            raw_document_present=True,
            document_age_hours=1,
        ),
        IdentityOperation(
            operation_id="op-assert-001",
            action=IdentityAction.ISSUE_ASSERTION,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-001",
            actor_roles=("identity_verifier",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_a,
            raw_document_present=True,
            document_age_hours=1,
            identity_verification_succeeded=True,
            requested_claims=("identity_verified", "age_over_21"),
        ),
        IdentityOperation(
            operation_id="op-export-bulk",
            action=IdentityAction.EXPORT_ASSERTIONS,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-001",
            actor_roles=("identity_admin",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_a,
            records_requested=1000,
        ),
        IdentityOperation(
            operation_id="op-export-window",
            action=IdentityAction.EXPORT_ASSERTIONS,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-001",
            actor_roles=("auditor",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_a,
            records_requested=75,
            records_exported_in_window_before=450,
        ),
        IdentityOperation(
            operation_id="op-cross-tenant",
            action=IdentityAction.READ_RAW_DOCUMENT,
            actor_tenant_id="alpha",
            resource_tenant_id="bravo",
            subject_ref="subj-bravo-007",
            actor_roles=("identity_verifier",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_b,
            raw_document_present=True,
            document_age_hours=2,
        ),
        IdentityOperation(
            operation_id="op-expired-raw",
            action=IdentityAction.READ_RAW_DOCUMENT,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-002",
            actor_roles=("identity_verifier",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_a,
            raw_document_present=True,
            document_age_hours=49,
        ),
        IdentityOperation(
            operation_id="op-weak-export",
            action=IdentityAction.EXPORT_ASSERTIONS,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-003",
            actor_roles=("identity_admin",),
            auth_strength=AuthStrength.PASSWORD,
            tenant_key_ref=key_a,
            records_requested=10,
        ),
        IdentityOperation(
            operation_id="op-bad-key-scope",
            action=IdentityAction.EXPORT_ASSERTIONS,
            actor_tenant_id="alpha",
            resource_tenant_id="alpha",
            subject_ref="subj-alpha-004",
            actor_roles=("auditor",),
            auth_strength=AuthStrength.HARDWARE_BACKED,
            tenant_key_ref=key_b,
            records_requested=10,
        ),
    )
    decisions = _evaluate_chain(operations, policy)
    assertion = issue_derived_assertion(
        assertion_id="assert-alpha-001",
        operation=operations[1],
        decision=decisions[1],
        values={"identity_verified": True, "age_over_21": True},
    )
    retention_records = (
        RetentionRecord(record_id="raw-alpha-recent", tenant_id="alpha", raw_document_present=True, age_hours=4),
        RetentionRecord(record_id="raw-alpha-expired", tenant_id="alpha", raw_document_present=True, age_hours=72),
        RetentionRecord(record_id="assertion-only", tenant_id="alpha", raw_document_present=False, age_hours=500),
    )
    purge_ids = records_requiring_purge(retention_records, policy)
    checks = IdentitySecurityAcceptance(
        legitimate_verification_allowed=decisions[0].allowed and decisions[0].delete_raw_after_operation,
        selective_assertion_allowed=decisions[1].allowed and decisions[1].minimize_to_assertion,
        raw_document_excluded_from_assertion=not assertion.raw_document_included,
        bulk_export_blocked=not decisions[2].allowed and "PER_REQUEST_EXPORT_LIMIT_EXCEEDED" in decisions[2].reasons,
        export_window_blocked=not decisions[3].allowed and "EXPORT_WINDOW_LIMIT_EXCEEDED" in decisions[3].reasons,
        cross_tenant_access_blocked=not decisions[4].allowed and "CROSS_TENANT_ACCESS_DENIED" in decisions[4].reasons,
        expired_raw_access_blocked=not decisions[5].allowed and decisions[5].delete_raw_after_operation and "RAW_RETENTION_EXPIRED" in decisions[5].reasons,
        weak_privileged_auth_blocked=not decisions[6].allowed and "HARDWARE_BACKED_AUTH_REQUIRED" in decisions[6].reasons,
        tenant_key_scope_blocked=not decisions[7].allowed and "TENANT_KEY_SCOPE_INVALID" in decisions[7].reasons,
        retention_purge_identified=purge_ids == ("raw-alpha-expired",),
        audit_chain_verified=verify_audit_chain(decisions),
        acceptance_pass=False,
    )
    acceptance = checks.model_copy(
        update={
            "acceptance_pass": all(
                value
                for key, value in checks.model_dump().items()
                if key != "acceptance_pass"
            )
        }
    )
    report = IdentitySecurityG1Report(
        policy=policy,
        decisions=decisions,
        assertion=assertion,
        purge_record_ids=purge_ids,
        audit_chain_terminal_digest=decisions[-1].event_digest,
        acceptance=acceptance,
    )
    digest = canonical_digest(report.model_dump(mode="json", exclude={"report_digest"}))
    return report.model_copy(update={"report_digest": digest})


def verify_identity_security_g1_report(report: IdentitySecurityG1Report) -> bool:
    expected_report_digest = canonical_digest(
        report.model_dump(mode="json", exclude={"report_digest"})
    )
    expected_assertion_digest = canonical_digest(
        report.assertion.model_dump(mode="json", exclude={"assertion_digest"})
    )
    return (
        report.report_digest == expected_report_digest
        and report.assertion.assertion_digest == expected_assertion_digest
        and report.audit_chain_terminal_digest == report.decisions[-1].event_digest
        and verify_audit_chain(report.decisions)
    )

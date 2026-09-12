import pytest
from pydantic import ValidationError

from worldshepherd_sara.identity_security_g1 import (
    AuthStrength,
    DerivedAssertion,
    DerivedClaim,
    IdentityAction,
    IdentityOperation,
    IdentitySecurityPolicy,
    evaluate_identity_operation,
    run_identity_security_g1_benchmark,
    verify_audit_chain,
    verify_identity_security_g1_report,
)


def test_identity_security_g1_default_report_passes_and_verifies():
    report = run_identity_security_g1_benchmark()
    assert report.acceptance.acceptance_pass
    assert verify_identity_security_g1_report(report)
    assert report.capability_status.value == "IMPLEMENTED_IN_SOFTWARE"
    assert not report.nist_conformity_claimed
    assert not report.production_hardening_validated
    assert not report.breach_prevention_claimed


def test_fail_closed_cases_are_blocked():
    report = run_identity_security_g1_benchmark()
    by_id = {decision.operation_id: decision for decision in report.decisions}

    assert not by_id["op-export-bulk"].allowed
    assert "PER_REQUEST_EXPORT_LIMIT_EXCEEDED" in by_id["op-export-bulk"].reasons

    assert not by_id["op-export-window"].allowed
    assert "EXPORT_WINDOW_LIMIT_EXCEEDED" in by_id["op-export-window"].reasons

    assert not by_id["op-cross-tenant"].allowed
    assert "CROSS_TENANT_ACCESS_DENIED" in by_id["op-cross-tenant"].reasons

    assert not by_id["op-expired-raw"].allowed
    assert by_id["op-expired-raw"].delete_raw_after_operation

    assert not by_id["op-weak-export"].allowed
    assert "HARDWARE_BACKED_AUTH_REQUIRED" in by_id["op-weak-export"].reasons

    assert not by_id["op-bad-key-scope"].allowed
    assert "TENANT_KEY_SCOPE_INVALID" in by_id["op-bad-key-scope"].reasons


def test_selective_assertion_never_contains_raw_document():
    report = run_identity_security_g1_benchmark()
    assert report.assertion.raw_document_included is False
    assert {claim.name for claim in report.assertion.claims} == {
        "identity_verified",
        "age_over_21",
    }
    with pytest.raises(ValidationError):
        DerivedAssertion(
            assertion_id="bad-assertion",
            tenant_id="alpha",
            subject_ref="subj-alpha-001",
            claims=(DerivedClaim(name="identity_verified", value=True),),
            source_operation_id="op-assert-001",
            raw_document_included=True,
        )


def test_unapproved_claim_is_denied():
    policy = IdentitySecurityPolicy()
    operation = IdentityOperation(
        operation_id="op-unapproved-claim",
        action=IdentityAction.ISSUE_ASSERTION,
        actor_tenant_id="alpha",
        resource_tenant_id="alpha",
        subject_ref="subj-alpha-009",
        actor_roles=("identity_verifier",),
        auth_strength=AuthStrength.HARDWARE_BACKED,
        tenant_key_ref="tenant/alpha/key/id-proofing-v1",
        identity_verification_succeeded=True,
        requested_claims=("full_driver_license_number",),
    )
    decision = evaluate_identity_operation(operation, policy)
    assert not decision.allowed
    assert "UNAPPROVED_DERIVED_CLAIM" in decision.reasons


def test_digest_and_audit_chain_detect_tampering():
    report = run_identity_security_g1_benchmark()
    assert verify_audit_chain(report.decisions)

    tampered_decision = report.decisions[3].model_copy(
        update={"previous_event_digest": "sha256:tampered"}
    )
    tampered_decisions = (
        *report.decisions[:3],
        tampered_decision,
        *report.decisions[4:],
    )
    assert not verify_audit_chain(tampered_decisions)

    tampered_report = report.model_copy(
        update={"purge_record_ids": ("raw-alpha-expired", "invented-record")}
    )
    assert not verify_identity_security_g1_report(tampered_report)

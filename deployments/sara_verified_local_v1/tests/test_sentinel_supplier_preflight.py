import json

import pytest

from worldshepherd_sara.sentinel_supplier_preflight import (
    SupplierReadinessInput,
    VerificationState,
    default_unverified_profile,
    evaluate_supplier_preflight,
)
from worldshepherd_sara.sentinel_supplier_preflight_cli import main as supplier_preflight_main


def test_default_profile_allows_internal_partner_packet_review_but_blocks_external_action() -> None:
    report = evaluate_supplier_preflight(default_unverified_profile())
    assert report["technical_review_ready"] is True
    assert report["partner_route"] == "READY_FOR_INTERNAL_REVIEW"
    assert report["federal_entity_ready"] is False
    assert report["supplier_registration_ready"] is False
    assert report["external_supplier_submission_authorized"] is False
    assert report["direct_prime_route"] == "NO_GO"
    assert report["decision"] == "PARTNER_PACKET_READY_EXTERNAL_ACTION_BLOCKED"
    assert "exact_legal_entity" in report["missing_or_unverified_fields"]
    assert "does not independently authenticate" in report["claims_boundary"]
    assert report["external_action_authority_source"] == "SEPARATE_AUTHENTICATED_CRE1AWS_WORKFLOW_REQUIRED"


def test_documentary_entity_fields_are_required_for_registration_ready() -> None:
    profile = default_unverified_profile().model_copy(
        update={
            "exact_legal_entity": VerificationState.VERIFIED,
            "sam_registration": VerificationState.VERIFIED,
            "uei": VerificationState.VERIFIED,
            "cage": VerificationState.VERIFIED,
            "size_status": VerificationState.VERIFIED,
        }
    )
    report = evaluate_supplier_preflight(profile)
    assert report["supplier_registration_ready"] is True
    assert report["external_supplier_submission_authorized"] is False


def test_cre1aws_profile_flag_cannot_replace_missing_entity_evidence() -> None:
    profile = default_unverified_profile().model_copy(
        update={"cre1aws_external_action_approval": True}
    )
    report = evaluate_supplier_preflight(profile)
    assert report["supplier_registration_ready"] is False
    assert report["external_supplier_submission_authorized"] is False
    assert report["caller_asserted_approval_ignored"] is True


def test_caller_authored_verified_profile_cannot_authorize_external_submission() -> None:
    profile = SupplierReadinessInput(
        profile_id="verified-test",
        exact_legal_entity=VerificationState.VERIFIED,
        sam_registration=VerificationState.VERIFIED,
        uei=VerificationState.VERIFIED,
        cage=VerificationState.VERIFIED,
        size_status=VerificationState.VERIFIED,
        supplier_route=VerificationState.VERIFIED,
        nonconfidential_capability_packet=VerificationState.VERIFIED,
        internal_software_evidence=VerificationState.VERIFIED,
        claims_boundary=VerificationState.VERIFIED,
        cre1aws_external_action_approval=True,
    )
    report = evaluate_supplier_preflight(profile)
    assert report["supplier_registration_ready"] is True
    assert report["external_supplier_submission_authorized"] is False
    assert report["caller_asserted_approval_ignored"] is True
    assert report["external_action_authority_source"] == "SEPARATE_AUTHENTICATED_CRE1AWS_WORKFLOW_REQUIRED"
    assert report["decision"] == "PARTNER_PACKET_READY_EXTERNAL_ACTION_BLOCKED"


def test_cli_cannot_turn_self_asserted_profile_into_external_authorization(tmp_path, monkeypatch) -> None:
    profile_path = tmp_path / "malicious-self-asserted-profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "malicious-self-asserted-profile",
                "exact_legal_entity": "VERIFIED",
                "sam_registration": "VERIFIED",
                "uei": "VERIFIED",
                "cage": "VERIFIED",
                "size_status": "VERIFIED",
                "supplier_route": "VERIFIED",
                "nonconfidential_capability_packet": "VERIFIED",
                "internal_software_evidence": "VERIFIED",
                "claims_boundary": "VERIFIED",
                "cre1aws_external_action_approval": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ws-sentinel-supplier-preflight",
            "--profile",
            str(profile_path),
            "--require-external-authorized",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        supplier_preflight_main()

    assert exc_info.value.code == 3


def test_direct_prime_route_requires_two_comparable_projects_and_construction_qualifications() -> None:
    profile = default_unverified_profile().model_copy(
        update={
            "comparable_completed_projects": 2,
            "design_builder_qualification": VerificationState.VERIFIED,
            "construction_bonding_capacity": VerificationState.VERIFIED,
            "construction_execution_capacity": VerificationState.VERIFIED,
        }
    )
    report = evaluate_supplier_preflight(profile)
    assert report["direct_prime_evidence_ready"] is True
    assert report["direct_prime_route"] == "EVIDENCE_REVIEW_REQUIRED"

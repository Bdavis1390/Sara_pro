from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.fasa import (
    CapabilityLevel,
    CapabilityRegistryEntry,
    FrontierActionCandidate,
    FrontierDisposition,
    FrontierSafetyPolicy,
)
from worldshepherd_sara.fasa_admission_evidence import (
    FASAAdmissionEvidence,
    FASAAdmissionEvidenceError,
    build_admission_evidence,
    verify_admission_evidence,
)
from worldshepherd_sara.fasa_approval_lease import VerifiedFASAApproval


def _registry() -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F4,
        maximum_authorized_level=CapabilityLevel.F4,
        evaluation_id="EVAL-001",
        evaluation_current=True,
    )


def _candidate(level: CapabilityLevel = CapabilityLevel.F2) -> FrontierActionCandidate:
    return FrontierActionCandidate(
        action_id="ACT-001",
        model_id="model-A",
        model_version="1.0",
        capability_level=level,
        reversible=True,
        provenance_enabled=True,
        overwatch_enabled=True,
    )


def _verified_approval(now: datetime) -> VerifiedFASAApproval:
    return VerifiedFASAApproval(
        authorization_id="AUTH-001",
        model_id="model-A",
        model_version="1.0",
        capability_level=CapabilityLevel.F3,
        action_id="ACT-001",
        target_environment="staging",
        policy_id="WS-FASA-001",
        evaluation_id="EVAL-001",
        safety_case_id=None,
        independent_review_id=None,
        key_id="prime-key-1",
        key_fingerprint_sha256="a" * 64,
        nonce="0123456789abcdef",
        issued_at=now,
        expires_at=now + timedelta(seconds=60),
    )


def test_low_risk_allow_decision_builds_and_verifies_without_approval():
    now = datetime(2026, 9, 11, 19, 0, tzinfo=timezone.utc)
    evidence = build_admission_evidence(
        _candidate(CapabilityLevel.F2),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        FrontierDisposition.ALLOW,
        ["bounded automatic-execution gates satisfied"],
        assessed_at=now,
    )
    assert evidence.authorization_id is None
    verify_admission_evidence(evidence)


def test_f3_allow_requires_verified_approval_evidence():
    now = datetime(2026, 9, 11, 19, 0, tzinfo=timezone.utc)
    with pytest.raises(
        FASAAdmissionEvidenceError,
        match="requires verified approval evidence",
    ):
        build_admission_evidence(
            _candidate(CapabilityLevel.F3),
            _registry(),
            FrontierSafetyPolicy(policy_id="WS-FASA-001"),
            FrontierDisposition.ALLOW,
            ["approval gates satisfied"],
            assessed_at=now,
        )

    evidence = build_admission_evidence(
        _candidate(CapabilityLevel.F3),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        FrontierDisposition.ALLOW,
        ["approval gates satisfied"],
        verified_approval=_verified_approval(now),
        assessed_at=now,
    )
    assert evidence.authorization_id == "AUTH-001"
    assert evidence.approval_key_fingerprint_sha256 == "a" * 64
    verify_admission_evidence(evidence)


def test_approval_must_bind_to_candidate_policy_and_evaluation():
    now = datetime(2026, 9, 11, 19, 0, tzinfo=timezone.utc)
    wrong = _verified_approval(now).model_copy(update={"action_id": "ACT-OTHER"})
    with pytest.raises(FASAAdmissionEvidenceError, match="not bound"):
        build_admission_evidence(
            _candidate(CapabilityLevel.F3),
            _registry(),
            FrontierSafetyPolicy(policy_id="WS-FASA-001"),
            FrontierDisposition.ALLOW,
            ["approval gates satisfied"],
            verified_approval=wrong,
            assessed_at=now,
        )


def test_tampering_with_digest_bound_field_is_detected():
    now = datetime(2026, 9, 11, 19, 0, tzinfo=timezone.utc)
    evidence = build_admission_evidence(
        _candidate(CapabilityLevel.F2),
        _registry(),
        FrontierSafetyPolicy(policy_id="WS-FASA-001"),
        FrontierDisposition.DENIED,
        ["simulated denial"],
        assessed_at=now,
    )
    tampered = FASAAdmissionEvidence.model_validate(
        {**evidence.model_dump(), "reasons": ("tampered reason",)}
    )
    with pytest.raises(FASAAdmissionEvidenceError, match="digest mismatch"):
        verify_admission_evidence(tampered)


def test_naive_assessment_timestamp_is_rejected():
    with pytest.raises(FASAAdmissionEvidenceError, match="timezone-aware"):
        build_admission_evidence(
            _candidate(CapabilityLevel.F2),
            _registry(),
            FrontierSafetyPolicy(policy_id="WS-FASA-001"),
            FrontierDisposition.DENIED,
            ["simulated denial"],
            assessed_at=datetime(2026, 9, 11, 19, 0),
        )

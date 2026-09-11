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
    FASAAdmissionEvidenceError,
    build_admission_evidence,
    verify_admission_evidence,
)
from worldshepherd_sara.fasa_approval_lease import VerifiedFASAApproval


def _registry() -> CapabilityRegistryEntry:
    return CapabilityRegistryEntry(
        model_id="model-A",
        model_version="1.0",
        assessed_level=CapabilityLevel.F2,
        maximum_authorized_level=CapabilityLevel.F2,
        evaluation_id="EVAL-002",
        evaluation_current=True,
    )


def _approval(now: datetime) -> VerifiedFASAApproval:
    return VerifiedFASAApproval(
        authorization_id="AUTH-F2-IRREVERSIBLE",
        model_id="model-A",
        model_version="1.0",
        capability_level=CapabilityLevel.F2,
        action_id="ACT-F2-IRREVERSIBLE",
        target_environment="staging",
        policy_id="WS-FASA-001",
        evaluation_id="EVAL-002",
        safety_case_id=None,
        independent_review_id=None,
        key_id="prime-key-1",
        key_fingerprint_sha256="b" * 64,
        nonce="fedcba9876543210",
        issued_at=now,
        expires_at=now + timedelta(seconds=60),
    )


def test_irreversible_f2_allow_still_requires_verified_approval_evidence():
    now = datetime(2026, 9, 11, 19, 10, tzinfo=timezone.utc)
    candidate = FrontierActionCandidate(
        action_id="ACT-F2-IRREVERSIBLE",
        model_id="model-A",
        model_version="1.0",
        capability_level=CapabilityLevel.F2,
        reversible=False,
        provenance_enabled=True,
        overwatch_enabled=True,
    )
    policy = FrontierSafetyPolicy(policy_id="WS-FASA-001")

    with pytest.raises(FASAAdmissionEvidenceError, match="approval-gated candidate"):
        build_admission_evidence(
            candidate,
            _registry(),
            policy,
            FrontierDisposition.ALLOW,
            ["simulated approval-gated allow"],
            assessed_at=now,
        )

    evidence = build_admission_evidence(
        candidate,
        _registry(),
        policy,
        FrontierDisposition.ALLOW,
        ["verified human authorization present"],
        verified_approval=_approval(now),
        assessed_at=now,
    )
    assert evidence.authorization_id == "AUTH-F2-IRREVERSIBLE"
    verify_admission_evidence(evidence)

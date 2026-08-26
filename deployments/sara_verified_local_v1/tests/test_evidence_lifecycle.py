from __future__ import annotations

import pytest

from worldshepherd_sara.evidence_lifecycle import revoke_evidence, supersede_evidence
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    EvidenceScope,
    QualificationEvidenceRecord,
    ResultStatus,
    SupersessionState,
)


def _record() -> QualificationEvidenceRecord:
    return QualificationEvidenceRecord(
        qualification_id="WS-QE-2026-9001",
        requirement_id="PRE-RD-2026-0001",
        test_id="lifecycle-test",
        evidence_scope=EvidenceScope.SOFTWARE,
        capability_status=CapabilityStatus.PROVEN_INTERNALLY,
        environment_digest="sha256:env",
        configuration_digest="sha256:config",
        result=ResultStatus.PASS,
        rationale="synthetic lifecycle fixture",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )


def test_evidence_can_be_superseded_without_deleting_prior_record():
    old = _record()
    updated = supersede_evidence(
        old,
        superseded_by="WS-QE-2026-9002",
        reviewer="identified-human-reviewer",
        reviewed_utc="2026-08-26T01:00:00Z",
    )
    assert old.supersession.state == SupersessionState.CURRENT
    assert updated.supersession.state == SupersessionState.SUPERSEDED
    assert updated.supersession.superseded_by == "WS-QE-2026-9002"


def test_evidence_revocation_retains_negative_reason_and_fails_repeat_revoke():
    revoked = revoke_evidence(
        _record(),
        reviewer="identified-human-reviewer",
        reviewed_utc="2026-08-26T01:00:00Z",
        reason="fixture invalidated",
    )
    assert revoked.supersession.state == SupersessionState.REVOKED
    assert revoked.negative_evidence[-1]["revocation_reason"] == "fixture invalidated"
    with pytest.raises(ValueError):
        revoke_evidence(
            revoked,
            reviewer="identified-human-reviewer",
            reviewed_utc="2026-08-26T02:00:00Z",
            reason="repeat",
        )

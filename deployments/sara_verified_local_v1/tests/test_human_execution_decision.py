from datetime import datetime, timezone

import pytest

from worldshepherd_sara.human_execution_decision import (
    HumanExecutionAction,
    HumanExecutionDecisionError,
    assert_human_approval_matches,
    record_human_execution_decision,
    verify_human_execution_decision,
)


def test_human_approval_is_hash_bound_to_exact_action_digest():
    now = datetime.now(timezone.utc)
    record = record_human_execution_decision(
        decision_id="HUMAN-001",
        action_id="ACTION-001",
        action_digest_sha256="sha256:" + "1" * 64,
        decision_by="CRE1AWS",
        decided_at=now,
        action=HumanExecutionAction.APPROVE,
        rationale="Approved bounded read-only validation.",
    )
    assert verify_human_execution_decision(record)
    assert_human_approval_matches(
        record,
        action_id="ACTION-001",
        action_digest_sha256="sha256:" + "1" * 64,
    )
    with pytest.raises(HumanExecutionDecisionError, match="digest mismatch"):
        assert_human_approval_matches(
            record,
            action_id="ACTION-001",
            action_digest_sha256="sha256:" + "2" * 64,
        )


def test_reject_never_satisfies_approval_gate():
    now = datetime.now(timezone.utc)
    record = record_human_execution_decision(
        decision_id="HUMAN-002",
        action_id="ACTION-001",
        action_digest_sha256="sha256:" + "1" * 64,
        decision_by="CRE1AWS",
        decided_at=now,
        action=HumanExecutionAction.REJECT,
        rationale="Rejected for test.",
    )
    with pytest.raises(HumanExecutionDecisionError, match="not APPROVE"):
        assert_human_approval_matches(
            record,
            action_id="ACTION-001",
            action_digest_sha256="sha256:" + "1" * 64,
        )

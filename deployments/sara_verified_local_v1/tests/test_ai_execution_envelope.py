from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.ai_execution_envelope import (
    AIExecutionEnvelopeError,
    assert_execution_authorized,
    build_ai_execution_envelope,
)
from worldshepherd_sara.human_execution_decision import (
    HumanExecutionAction,
    record_human_execution_decision,
)
from worldshepherd_sara.prime_action_authorization import VerifiedPrimeActionAuthorization


def _envelope():
    return build_ai_execution_envelope(
        action_id="ACTION-001",
        provider="OPENAI",
        provider_operation="RESPONSES_CREATE",
        model="gpt-test",
        tools=["read_system_status"],
        resource_scope=["system:status"],
        requested_authority=1,
        reversible=True,
        side_effect_class="READ_ONLY",
        request_payload={"input": "status"},
        policy_id="POLICY-001",
        policy_sha256="sha256:" + "2" * 64,
        execution_id="AI-EXEC-001",
        created_at=datetime.now(timezone.utc),
    )


def _authorization(envelope, *, human=False, decision=None):
    now = datetime.now(timezone.utc)
    return VerifiedPrimeActionAuthorization(
        authorization_id="ACT-AUTH-001",
        action_id=envelope.action_id,
        prime_id="PRIME-001",
        provider=envelope.provider,
        provider_operation=envelope.provider_operation,
        model_allowlist=[envelope.model],
        tool_allowlist=list(envelope.tools),
        resource_scope=list(envelope.resource_scope),
        requested_authority=envelope.requested_authority,
        reversible=envelope.reversible,
        side_effect_class=envelope.side_effect_class,
        policy_id=envelope.policy_id,
        policy_sha256=envelope.policy_sha256,
        policy_disposition=("HUMAN_REVIEW_REQUIRED" if human else "AUTO_ELIGIBLE"),
        request_sha256=envelope.request_sha256,
        human_approval_required=human,
        human_decision_id=(decision.decision_id if decision else None),
        human_decision_sha256=(decision.decision_sha256 if decision else None),
        key_id="PS-ACT-K1",
        key_fingerprint_sha256="f" * 64,
        nonce="nonce-action-0123456789",
        issued_at=now,
        expires_at=now + timedelta(minutes=5),
    )


def test_exact_envelope_passes_and_mutated_payload_changes_digest():
    envelope = _envelope()
    auth = _authorization(envelope)
    assert_execution_authorized(envelope, auth)
    with pytest.raises(ValueError, match="request_sha256"):
        envelope.model_copy(update={"request_payload": {"input": "different"}}).model_validate(
            envelope.model_copy(update={"request_payload": {"input": "different"}}).model_dump()
        )


def test_model_and_tool_must_be_within_signed_allowlists():
    envelope = _envelope()
    auth = _authorization(envelope).model_copy(update={"model_allowlist": ["different"]})
    with pytest.raises(AIExecutionEnvelopeError, match="model"):
        assert_execution_authorized(envelope, auth)


def test_human_review_requires_exact_approved_digest_and_decision_hash():
    envelope = _envelope()
    decision = record_human_execution_decision(
        decision_id="HUMAN-001",
        action_id=envelope.action_id,
        action_digest_sha256=envelope.request_sha256,
        decision_by="CRE1AWS",
        decided_at=datetime.now(timezone.utc),
        action=HumanExecutionAction.APPROVE,
        rationale="Approve exact bounded execution digest.",
    )
    auth = _authorization(envelope, human=True, decision=decision)
    assert_execution_authorized(envelope, auth, human_decision=decision)

    changed = decision.model_copy(update={"rationale": "tampered"})
    with pytest.raises(AIExecutionEnvelopeError, match="integrity"):
        assert_execution_authorized(envelope, auth, human_decision=changed)

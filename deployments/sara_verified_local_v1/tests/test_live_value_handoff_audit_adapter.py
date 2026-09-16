from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from worldshepherd_sara.event_outbox import drain_event_outbox
from worldshepherd_sara.live_value_execution_handoff import (
    LiveValueExecutionHandoffAssessment,
    LiveValueExecutionIntent,
    execution_intent_sha256,
)
from worldshepherd_sara.live_value_handoff_audit_adapter import (
    LiveValueHandoffAuditError,
    live_value_handoff_projection,
)
from worldshepherd_sara.qcrypto_audit_adapter import (
    new_qcrypto_audit_instance_id,
    qcrypto_decision_digest,
    queue_qcrypto_projection_patch,
)
from worldshepherd_sara.qcrypto_audit_verifier import verify_qcrypto_audit_chain
from worldshepherd_sara.storage import DurableStore


def intent():
    return LiveValueExecutionIntent(
        chain="fixture-chain",
        network="fixture-network",
        asset="FIX",
        amount_atomic=1,
        fee_ceiling_atomic=1,
        source_custody_ref="fixture-custody",
        destination_commitment_sha256="1" * 64,
        unsigned_transaction_digest_sha256="2" * 64,
        review_package_sha256="3" * 64,
        production_revision="4" * 40,
        change_ticket_id="CHG-FIXTURE-1",
        intent_nonce="fixture-intent-0001",
        valid_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def assessment(bound_intent: LiveValueExecutionIntent):
    return LiveValueExecutionHandoffAssessment(
        schema="WS-LIVE-VALUE-EXECUTION-HANDOFF-V1",
        state="READY_FOR_EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF",
        handoff_package_sha256="a" * 64,
        intent_sha256=execution_intent_sha256(bound_intent),
        approval_id="LVA-FIXTURE-1",
        approver_id="fixture-human",
        human_live_value_approval_verified=True,
        external_signer_handoff_ready=True,
        point_of_value_moving_execution_reached=True,
        qcrypto_execution_authority=False,
        qcrypto_live_value_authorized=False,
        qcrypto_private_key_operations_permitted=False,
        qcrypto_broadcast_permitted=False,
        blockers=(),
        warnings=(),
        next_action="EXTERNAL_HUMAN_OPERATED_SIGNER_MAY_SIGN_AND_BROADCAST_ONLY_WITHIN_THE_BOUND_INTENT",
    )


def test_ready_handoff_maps_to_existing_four_stage_qcrypto_audit_contract():
    tx = intent()
    projection = live_value_handoff_projection(assessment(tx), tx)
    assert projection["echo_state"] == "LIVE_VALUE_INTENT_APPROVAL_AND_PREFLIGHT_BOUND"
    assert projection["prime_state"] == "LIVE_VALUE_POLICY_HANDOFF_READY"
    assert projection["sara_state"] == "EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF_READY"
    assert projection["overwatch_state"] == "LIVE_VALUE_EXECUTION_WINDOW_MONITOR_ONLY"
    assert projection["human_approval_required"] is True
    assert projection["execution_authority"] is False
    assert projection["live_value_authorized"] is False
    assert projection["correlation_id"] == "sha256:" + "a" * 64


def test_ready_handoff_persists_and_reconstructs_through_native_sara_audit(tmp_path):
    tx = intent()
    projection = live_value_handoff_projection(assessment(tx), tx)
    decision_digest = qcrypto_decision_digest(projection)
    audit_instance_id = new_qcrypto_audit_instance_id()
    store = DurableStore(tmp_path / "data")

    def operation(registry):
        patch, event_ids = queue_qcrypto_projection_patch(
            registry,
            projection,
            actor="SSPADAWANZZ",
            audit_instance_id=audit_instance_id,
        )
        return patch, event_ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert len(set(event_ids)) == 4
    assert drain_event_outbox(store, limit=4) == 4

    records = store.read_audit(50)
    verification = verify_qcrypto_audit_chain(
        records,
        decision_digest=decision_digest,
        audit_instance_id=audit_instance_id,
    )
    assert verification.verdict == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert verification.complete is True
    assert verification.consistent is True
    assert verification.stages_present == ("ECHO", "PRIME", "SARA", "OVERWATCH")
    assert verification.execution_authority is False
    assert verification.live_value_authorized is False


def test_adapter_rejects_authority_escalation():
    tx = intent()
    bad = replace(assessment(tx), qcrypto_broadcast_permitted=True)
    with pytest.raises(LiveValueHandoffAuditError, match="authority flags"):
        live_value_handoff_projection(bad, tx)


def test_adapter_rejects_intent_substitution():
    tx = intent()
    other = tx.model_copy(update={"amount_atomic": 2})
    with pytest.raises(LiveValueHandoffAuditError, match="not bound"):
        live_value_handoff_projection(assessment(tx), other)

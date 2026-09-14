from __future__ import annotations

from copy import deepcopy

from worldshepherd_sara.event_outbox import drain_event_outbox
from worldshepherd_sara.qcrypto_audit_adapter import (
    QCRYPTO_AUDIT_SCHEMA,
    qcrypto_decision_digest,
    queue_qcrypto_projection_patch,
)
from worldshepherd_sara.qcrypto_audit_verifier import verify_qcrypto_audit_chain
from worldshepherd_sara.storage import DurableStore


def projection(**overrides):
    value = {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": "asset-verify-001",
        "echo_state": "ECHO_PROVENANCE_ACCEPTED",
        "prime_state": "PRIME_RECOMMENDS_PRIORITY_MIGRATION_PLAN",
        "sara_state": "SARA_PLAN_AUTHORIZED",
        "overwatch_state": "OVERWATCH_TRACK_AUTHORIZED_PLAN",
        "priority": "P0_MIGRATION_PRIORITY",
        "human_approval_required": True,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": "INTERNAL_PQC_CONTROL_PLANE_NOT_FEDERAL_COMPLIANCE",
        "correlation_id": "QCRYPTO-VERIFY-001",
    }
    value.update(overrides)
    return value


def delivered_records(tmp_path):
    store = DurableStore(tmp_path / "data")
    item = projection()

    def operation(registry):
        patch, event_ids = queue_qcrypto_projection_patch(
            registry,
            item,
            actor="admin",
        )
        return patch, event_ids

    event_ids = store.transact_registry(operation)
    assert len(event_ids) == 4
    assert drain_event_outbox(store, limit=4) == 4
    return item, store.read_audit(20)


def test_complete_chain_reconstructs_without_authority_promotion(tmp_path):
    item, records = delivered_records(tmp_path)
    digest = qcrypto_decision_digest(item)
    result = verify_qcrypto_audit_chain(records, decision_digest=digest)

    assert result.verdict == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert result.complete is True
    assert result.consistent is True
    assert result.stages_present == ("ECHO", "PRIME", "SARA", "OVERWATCH")
    assert result.missing_stages == ()
    assert result.execution_authority is False
    assert result.live_value_authorized is False
    assert result.federal_compliance_established is False
    assert result.ws_cae_conformance_established is False


def test_missing_stage_is_detected(tmp_path):
    item, records = delivered_records(tmp_path)
    digest = qcrypto_decision_digest(item)
    records = [record for record in records if record.get("event") != "qcrypto_overwatch_state"]

    result = verify_qcrypto_audit_chain(records, decision_digest=digest)

    assert result.verdict == "INCOMPLETE_AUDIT_CHAIN"
    assert result.complete is False
    assert result.consistent is True
    assert result.missing_stages == ("OVERWATCH",)


def test_cross_stage_tampering_is_detected(tmp_path):
    item, records = delivered_records(tmp_path)
    digest = qcrypto_decision_digest(item)
    tampered = deepcopy(records)
    prime = next(record for record in tampered if record.get("event") == "qcrypto_prime_state")
    prime["payload"]["priority"] = "P3_MONITOR"

    result = verify_qcrypto_audit_chain(tampered, decision_digest=digest)

    assert result.verdict == "INCONSISTENT_AUDIT_CHAIN"
    assert result.consistent is False
    assert any("priority" in reason for reason in result.reasons)


def test_authority_escalation_inside_audit_record_is_detected(tmp_path):
    item, records = delivered_records(tmp_path)
    digest = qcrypto_decision_digest(item)
    tampered = deepcopy(records)
    sara = next(record for record in tampered if record.get("event") == "qcrypto_sara_state")
    sara["payload"]["execution_authority"] = True

    result = verify_qcrypto_audit_chain(tampered, decision_digest=digest)

    assert result.verdict == "INCONSISTENT_AUDIT_CHAIN"
    assert result.consistent is False
    assert any("execution_authority" in reason for reason in result.reasons)


def test_identical_at_least_once_replay_is_tolerated(tmp_path):
    item, records = delivered_records(tmp_path)
    digest = qcrypto_decision_digest(item)
    replayed = list(records)
    replayed.append(deepcopy(next(record for record in records if record.get("event") == "qcrypto_echo_state")))

    result = verify_qcrypto_audit_chain(replayed, decision_digest=digest)

    assert result.verdict == "INTERNALLY_RECONSTRUCTED_AUDIT_CHAIN"
    assert result.complete is True
    assert result.consistent is True
    assert result.matching_record_count == 5
    assert result.logical_event_count == 4


def test_no_matching_digest_is_not_promoted(tmp_path):
    _item, records = delivered_records(tmp_path)
    result = verify_qcrypto_audit_chain(
        records,
        decision_digest="sha256:" + "0" * 64,
    )

    assert result.verdict == "NO_MATCHING_AUDIT_EVIDENCE"
    assert result.complete is False
    assert result.consistent is False

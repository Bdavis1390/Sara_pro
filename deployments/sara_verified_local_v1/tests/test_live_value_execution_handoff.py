from __future__ import annotations

import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.mldsa import MLDSA65PrivateKey

from worldshepherd_sara.live_value_execution_handoff import (
    HUMAN_APPROVAL_CONTEXT,
    ExternalExecutionPreflight,
    HumanLiveValueApproval,
    HumanLiveValueApprovalVerifier,
    LiveValueExecutionIntent,
    LiveValueHandoffError,
    assess_live_value_execution_handoff,
    canonical_human_approval_message,
    execution_intent_sha256,
)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def fixture(now: datetime | None = None):
    current = now or datetime(2026, 9, 16, 2, 20, tzinfo=timezone.utc)
    key = MLDSA65PrivateKey.generate()
    public_bytes = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    signer_fp = "7" * 64
    network_id = "8" * 64
    intent = LiveValueExecutionIntent(
        chain="Algorand",
        network="mainnet-v1.0",
        asset="ALGO",
        amount_atomic=1_000_000,
        fee_ceiling_atomic=10_000,
        source_custody_ref="external-custody://canary-001",
        destination_commitment_sha256="1" * 64,
        unsigned_transaction_digest_sha256="2" * 64,
        review_package_sha256="3" * 64,
        production_revision="4" * 40,
        change_ticket_id="CHG-LVC-001",
        intent_nonce="intent-nonce-000001",
        valid_until=current + timedelta(minutes=10),
    )
    unsigned = HumanLiveValueApproval(
        approver_id="CRE1AWS",
        approval_id="LVA-001",
        key_id="human-approval-key-1",
        intent_sha256=execution_intent_sha256(intent),
        review_package_sha256=intent.review_package_sha256,
        destination_commitment_sha256=intent.destination_commitment_sha256,
        external_signer_fingerprint_sha256=signer_fp,
        network_identity_sha256=network_id,
        maximum_amount_atomic=1_000_000,
        maximum_fee_atomic=10_000,
        change_ticket_id=intent.change_ticket_id,
        production_revision=intent.production_revision,
        issued_at=current - timedelta(seconds=10),
        expires_at=current + timedelta(minutes=5),
        nonce="approval-nonce-0001",
        signature_b64url="UNSIGNED",
    )
    signature = key.sign(canonical_human_approval_message(unsigned), HUMAN_APPROVAL_CONTEXT)
    approval = unsigned.model_copy(update={"signature_b64url": b64url(signature)})
    verifier = HumanLiveValueApprovalVerifier(
        public_keys_b64url={"human-approval-key-1": b64url(public_bytes)}
    )
    verified = verifier.verify(approval, intent, now=current)
    preflight = ExternalExecutionPreflight(
        intent_sha256=execution_intent_sha256(intent),
        approval_id=verified.approval_id,
        external_signer_fingerprint_sha256=signer_fp,
        network_identity_sha256=network_id,
        destination_commitment_sha256=intent.destination_commitment_sha256,
        observed_fee_atomic=1_000,
        destination_allowlist_match=True,
        balance_or_utxo_sufficient=True,
        nonce_or_outpoint_reserved=True,
        simulation_or_policy_check_passed=True,
        monitoring_ready=True,
        pause_ready=True,
        rollback_ready=True,
    )
    return current, key, intent, approval, verifier, verified, preflight


def test_complete_handoff_reaches_last_boundary_before_value_execution():
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=preflight,
    )
    assert result.state == "READY_FOR_EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF"
    assert result.external_signer_handoff_ready is True
    assert result.point_of_value_moving_execution_reached is True
    assert result.human_live_value_approval_verified is True
    assert result.handoff_package_sha256 is not None
    assert len(result.handoff_package_sha256) == 64
    assert result.qcrypto_execution_authority is False
    assert result.qcrypto_live_value_authorized is False
    assert result.qcrypto_private_key_operations_permitted is False
    assert result.qcrypto_broadcast_permitted is False


def test_tampered_human_approval_signature_is_rejected():
    current, _, intent, approval, verifier, _, _ = fixture()
    raw = base64.urlsafe_b64decode(approval.signature_b64url + "=" * (-len(approval.signature_b64url) % 4))
    tampered = bytes([raw[0] ^ 1]) + raw[1:]
    bad = approval.model_copy(update={"signature_b64url": b64url(tampered)})
    with pytest.raises(LiveValueHandoffError, match="invalid human live-value approval signature"):
        verifier.verify(bad, intent, now=current)


def test_approval_cannot_be_reused_for_modified_transaction_intent():
    current, _, intent, approval, verifier, _, _ = fixture()
    changed = intent.model_copy(update={"amount_atomic": intent.amount_atomic + 1})
    with pytest.raises(LiveValueHandoffError, match="intent_sha256"):
        verifier.verify(approval, changed, now=current)


def test_amount_and_fee_cannot_exceed_human_caps():
    current, key, intent, approval, verifier, _, _ = fixture()
    over_amount = intent.model_copy(update={"amount_atomic": 1_000_001})
    unsigned = approval.model_copy(
        update={
            "intent_sha256": execution_intent_sha256(over_amount),
            "signature_b64url": "UNSIGNED",
        }
    )
    signed = unsigned.model_copy(
        update={
            "signature_b64url": b64url(
                key.sign(canonical_human_approval_message(unsigned), HUMAN_APPROVAL_CONTEXT)
            )
        }
    )
    with pytest.raises(LiveValueHandoffError, match="amount exceeds"):
        verifier.verify(signed, over_amount, now=current)


def test_expired_approval_is_rejected():
    current, _, intent, approval, verifier, _, _ = fixture()
    with pytest.raises(LiveValueHandoffError, match="expired"):
        verifier.verify(approval, intent, now=current + timedelta(minutes=6))


def test_wrong_external_signer_blocks_handoff():
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, external_signer_fingerprint_sha256="9" * 64),
    )
    assert result.state == "VALUE_EXECUTION_HANDOFF_BLOCKED"
    assert any("signer fingerprint" in item for item in result.blockers)


def test_wrong_network_identity_blocks_handoff():
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, network_identity_sha256="a" * 64),
    )
    assert result.state == "VALUE_EXECUTION_HANDOFF_BLOCKED"
    assert any("network identity" in item for item in result.blockers)


def test_consumed_approval_cannot_be_replayed():
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, approval_consumed=True),
    )
    assert result.state == "VALUE_EXECUTION_HANDOFF_BLOCKED"
    assert any("already been consumed" in item for item in result.blockers)


@pytest.mark.parametrize("field", ["signed_payload_present", "private_key_material_present", "broadcast_requested"])
def test_qcrypto_stops_before_signing_key_material_or_broadcast(field):
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_READY_PENDING_EXPLICIT_HUMAN_APPROVAL",
        intent=intent,
        verified_approval=verified,
        preflight=replace(preflight, **{field: True}),
    )
    assert result.state == "VALUE_EXECUTION_HANDOFF_BLOCKED"
    assert result.external_signer_handoff_ready is False
    assert result.qcrypto_execution_authority is False
    assert result.qcrypto_private_key_operations_permitted is False
    assert result.qcrypto_broadcast_permitted is False


def test_legacy_boolean_approval_state_is_not_accepted_as_upstream_boundary():
    _, _, intent, _, _, verified, preflight = fixture()
    result = assess_live_value_execution_handoff(
        upstream_readiness_state="LVC_AUTHORIZED_FOR_BOUNDED_EXECUTION",
        intent=intent,
        verified_approval=verified,
        preflight=preflight,
    )
    assert result.state == "VALUE_EXECUTION_HANDOFF_BLOCKED"
    assert any("explicit-human-approval boundary" in item for item in result.blockers)

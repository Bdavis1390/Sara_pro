"""Native SARA audit projection for a completed live-value execution handoff.

The projection records the last QCRYPTO-controlled state before an external
human-operated signer may act.  It does not carry transaction bytes, private key
material, signatures, or broadcast authority.
"""

from __future__ import annotations

import re

from .live_value_execution_handoff import (
    LiveValueExecutionHandoffAssessment,
    LiveValueExecutionIntent,
    execution_intent_sha256,
)
from .qcrypto_audit_adapter import QCRYPTO_AUDIT_SCHEMA, qcrypto_outbox_events


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LiveValueHandoffAuditError(ValueError):
    pass


def live_value_handoff_projection(
    assessment: LiveValueExecutionHandoffAssessment,
    intent: LiveValueExecutionIntent,
) -> dict:
    """Map one verified external-signer handoff into the existing QCRYPTO audit schema."""

    if assessment.state != "READY_FOR_EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF":
        raise LiveValueHandoffAuditError("live-value handoff assessment is not ready")
    if not assessment.external_signer_handoff_ready:
        raise LiveValueHandoffAuditError("external signer handoff is not ready")
    if not assessment.point_of_value_moving_execution_reached:
        raise LiveValueHandoffAuditError("value-moving execution boundary was not reached")
    if not assessment.human_live_value_approval_verified:
        raise LiveValueHandoffAuditError("human live-value approval is not verified")
    if any(
        (
            assessment.qcrypto_execution_authority,
            assessment.qcrypto_live_value_authorized,
            assessment.qcrypto_private_key_operations_permitted,
            assessment.qcrypto_broadcast_permitted,
        )
    ):
        raise LiveValueHandoffAuditError("QCRYPTO authority flags must remain false at handoff")

    handoff_digest = assessment.handoff_package_sha256
    if not isinstance(handoff_digest, str) or not _HEX64.fullmatch(handoff_digest):
        raise LiveValueHandoffAuditError("handoff package digest is invalid")
    expected_intent = execution_intent_sha256(intent)
    if assessment.intent_sha256 != expected_intent:
        raise LiveValueHandoffAuditError("handoff assessment is not bound to the supplied intent")

    return {
        "schema": QCRYPTO_AUDIT_SCHEMA,
        "asset_id": f"LIVE-VALUE-HANDOFF:{handoff_digest}",
        "echo_state": "LIVE_VALUE_INTENT_APPROVAL_AND_PREFLIGHT_BOUND",
        "prime_state": "LIVE_VALUE_POLICY_HANDOFF_READY",
        "sara_state": "EXTERNAL_SIGNER_VALUE_EXECUTION_HANDOFF_READY",
        "overwatch_state": "LIVE_VALUE_EXECUTION_WINDOW_MONITOR_ONLY",
        "priority": "LIVE_VALUE_CANARY_EXECUTION_HANDOFF",
        # The cryptographic approval is already verified, but a separate human
        # operator still controls the external signer/broadcast action.
        "human_approval_required": True,
        "migration_executed": False,
        "execution_authority": False,
        "live_value_authorized": False,
        "federal_compliance_established": False,
        "ws_cae_conformance_established": False,
        "claim_boundary": (
            "Native audit custody for the last QCRYPTO-controlled state before external value execution. "
            "An ML-DSA-65 human approval has been verified against the frozen intent, but QCRYPTO still "
            "does not possess signing keys, signed transaction bytes, broadcast authority, execution authority, "
            "Federal compliance, or WS-CAE conformance. External signer action remains separately human-operated."
        ),
        "correlation_id": f"sha256:{handoff_digest}",
    }


def live_value_handoff_outbox_events(
    assessment: LiveValueExecutionHandoffAssessment,
    intent: LiveValueExecutionIntent,
    *,
    actor: str,
    audit_instance_id: str | None = None,
) -> list[dict]:
    projection = live_value_handoff_projection(assessment, intent)
    return qcrypto_outbox_events(
        projection,
        actor=actor,
        audit_instance_id=audit_instance_id,
    )

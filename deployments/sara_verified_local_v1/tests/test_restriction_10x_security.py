from __future__ import annotations

import copy

import pytest

from worldshepherd_sara.models import AuditRecord
from worldshepherd_sara.restriction_observability import (
    RestrictionObservabilityError,
    project_restriction_audit_record,
)
from worldshepherd_sara.restriction_provenance import (
    RESTRICTION_AUTHORITY,
    RESTRICTION_EVENT,
    RESTRICTION_SCHEMA,
    RESTRICTION_SCHEMA_V1,
    RestrictionProvenanceError,
    capture_restriction,
    queue_restriction_event,
)


KEY = b"worldshepherd-10x-security-test-key-32-bytes-minimum"
APPROVED_SUMMARY = "Output was restricted; only bounded provenance is retained."
BASELINE_RESIDUAL_RISK_UNITS = 5
MAX_RESIDUAL_RATIO = 0.10


def evidence():
    return capture_restriction(
        fingerprint_key=KEY,
        action="BLOCK",
        reason_code="POLICY.TEN_X_GATE",
        source_system="CHAT_ASSISTANT",
        processor="POLICY_GATE",
        process_version="v2",
        policy_ref="CONTENT_POLICY",
        correlation_id="ten-x-001",
        raw_input="10x gate input must not persist",
        raw_generated="10x gate generated content must not persist",
        safe_summary=APPROVED_SUMMARY,
        metadata={
            "stage": "post_generation_policy_check",
            "claims_state": "IMPLEMENTED_IN_SOFTWARE",
            "attempt": 1,
        },
        occurred_at="2026-09-17T22:30:00+00:00",
    )


def audit_record(payload, *, actor=RESTRICTION_AUTHORITY):
    value = copy.deepcopy(payload)
    value["_outbox_event_id"] = f"SARA-EVENT-RESTRICTION-{value['restriction_id']}"
    value["_delivery_semantics"] = "AT_LEAST_ONCE"
    return AuditRecord(
        timestamp="2026-09-17T22:30:01+00:00",
        event=RESTRICTION_EVENT,
        actor=actor,
        payload=value,
    ).model_dump(mode="json")


def _accepts_projection(record) -> bool:
    try:
        project_restriction_audit_record(record)
        return True
    except RestrictionObservabilityError:
        return False


def test_g4_reduces_declared_g3_start_residual_risk_by_at_least_ten_x():
    item = evidence()
    document = item.semantic_document()

    # 1. G3-start queue helper allowed caller-selected audit actor.
    actor_override_possible = True
    try:
        queue_restriction_event({}, item, actor="UNTRUSTED")  # type: ignore[call-arg]
    except TypeError:
        actor_override_possible = False

    # 2. G3-start evidence did not bind the governed authority inside its identity.
    payload_authority_missing = (
        document.get("schema") != RESTRICTION_SCHEMA
        or document.get("authority") != RESTRICTION_AUTHORITY
    )

    # 3. G3-start observability did not reject an outer audit actor mismatch.
    outer_actor_mismatch_accepted = _accepts_projection(
        audit_record(document, actor="UNTRUSTED")
    )

    # 4. G3-start observability did not recompute semantic restriction identity.
    tampered = copy.deepcopy(document)
    tampered["reason_code"] = "POLICY.TAMPERED"
    semantic_tamper_with_stale_id_accepted = _accepts_projection(audit_record(tampered))

    # 5. G3-start had no V2-to-V1 downgrade identity check.
    downgraded = copy.deepcopy(document)
    downgraded["schema"] = RESTRICTION_SCHEMA_V1
    downgraded.pop("authority")
    downgrade_with_stale_v2_id_accepted = _accepts_projection(audit_record(downgraded))

    residual = sum(
        int(value)
        for value in (
            actor_override_possible,
            payload_authority_missing,
            outer_actor_mismatch_accepted,
            semantic_tamper_with_stale_id_accepted,
            downgrade_with_stale_v2_id_accepted,
        )
    )

    assert BASELINE_RESIDUAL_RISK_UNITS == 5
    assert residual / BASELINE_RESIDUAL_RISK_UNITS <= MAX_RESIDUAL_RATIO
    assert residual == 0


def test_g3_zero_tolerance_context_controls_do_not_regress():
    with pytest.raises(RestrictionProvenanceError):
        capture_restriction(
            fingerprint_key=KEY,
            action="BLOCK",
            reason_code="POLICY.TEN_X_GATE",
            source_system="CHAT_ASSISTANT",
            processor="POLICY_GATE",
            safe_summary="arbitrary caller text must not persist",
            metadata={
                "stage": "post_generation_policy_check",
                "claims_state": "IMPLEMENTED_IN_SOFTWARE",
                "attempt": 1,
            },
            occurred_at="2026-09-17T22:30:00+00:00",
        )

    with pytest.raises(RestrictionProvenanceError):
        capture_restriction(
            fingerprint_key=KEY,
            action="BLOCK",
            reason_code="POLICY.TEN_X_GATE",
            source_system="UNKNOWN_PROVIDER",
            processor="UNKNOWN_GATE",
            metadata={"note": "free form metadata must not persist"},
            occurred_at="2026-09-17T22:30:00+00:00",
        )

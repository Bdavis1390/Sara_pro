from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.external_gap_ledger import (
    ExternalGapLedger,
    ExternalGapRecord,
    GapClass,
    GapStatus,
    ledger_summary,
)


def gap_record(**overrides) -> ExternalGapRecord:
    values = {
        "gap_id": "WS-GAP-0001",
        "source_org": "Example Partner",
        "source_date": "2026-09-16",
        "source_channel": "email",
        "source_ref": "opaque-message-ref",
        "source_visibility": "CONTROLLED",
        "feedback_summary": "Partner requires independent validation before stronger claims.",
        "classification": "EXTERNAL_VALIDATION_GAP",
        "confidence": 0.95,
        "systemic_key": "independent-validation-depth",
        "authoritative_evidence_checked": ["issue:#155"],
        "route_issue_refs": ["#155"],
        "owner": "ACTIVE-1",
        "action": "Freeze an evaluator package and obtain independent reproduction.",
        "closure_evidence": [],
        "claims_effect": "Do not promote independently validated language until closure.",
        "status": "ROUTED",
    }
    values.update(overrides)
    return ExternalGapRecord.model_validate(values)


def test_open_external_validation_gap_fails_closed_for_claim_promotion():
    record = gap_record()
    assert record.classification == GapClass.EXTERNAL_VALIDATION_GAP
    assert record.claim_promotion_blocked is True


def test_partner_gap_fails_closed_until_closed():
    record = gap_record(
        classification="PARTNER_GAP",
        systemic_key="partner-owned-core",
    )
    assert record.claim_promotion_blocked is True


def test_venue_scope_mismatch_routes_without_promoting_or_blocking_capability():
    record = gap_record(
        classification="VENUE_SCOPE_MISMATCH",
        systemic_key="venue-fit",
        feedback_summary="The contribution is outside the current charter.",
        claims_effect="Route to a better-aligned venue; do not distort the charter.",
    )
    assert record.claim_promotion_blocked is False


def test_closed_fail_closed_gap_requires_evidence_and_then_unblocks():
    record = gap_record(
        status="CLOSED",
        closure_evidence=["external-evaluator-attestation:sha256:abc"],
    )
    assert record.status == GapStatus.CLOSED
    assert record.claim_promotion_blocked is False


def test_closed_gap_without_closure_evidence_is_rejected():
    with pytest.raises(ValidationError):
        gap_record(status="CLOSED", closure_evidence=[])


def test_routed_gap_requires_authoritative_route_issue():
    with pytest.raises(ValidationError):
        gap_record(route_issue_refs=[])


def test_duplicate_gap_ids_are_rejected():
    first = gap_record()
    second = gap_record(source_org="Second Partner")
    with pytest.raises(ValidationError):
        ExternalGapLedger(records=[first, second])


def test_systemic_counts_deduplicate_recurrence_signal():
    first = gap_record()
    second = gap_record(
        gap_id="WS-GAP-0002",
        source_org="Second Partner",
        classification="PROOF_SURFACE_GAP",
        systemic_key="independent-validation-depth",
        claims_effect="Expose the current evidence boundary clearly.",
    )
    ledger = ExternalGapLedger(records=[first, second])
    assert ledger.systemic_counts() == {"independent-validation-depth": 2}
    assert ledger.open_fail_closed_gap_ids() == ["WS-GAP-0001"]


def test_ledger_digest_and_summary_are_deterministic():
    ledger = ExternalGapLedger(records=[gap_record()])
    first = ledger_summary(ledger)
    second = ledger_summary(ledger)
    assert first == second
    assert len(first["ledger_sha256"]) == 64
    assert first["record_count"] == 1
    assert first["open_fail_closed_gap_ids"] == ["WS-GAP-0001"]

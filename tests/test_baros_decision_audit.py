"""Research-only audit replay and tamper-detection checks — synthetic only."""

from dataclasses import replace
import hashlib

import pytest

from baros.closed_loop import AdaptationThresholds, BiologicalState
from baros.decision_audit import (
    make_research_decision_audit,
    verify_research_decision_audit,
)

SOURCE_DIGEST = hashlib.sha256(b"synthetic-declared-source").hexdigest()
OTHER_DIGEST = hashlib.sha256(b"synthetic-altered-source").hexdigest()


def _state(phase: int, *, changed=False, quality=0.96) -> BiologicalState:
    return BiologicalState(
        phase_index=phase,
        alpha_per_gy=(0.30, 0.31),
        beta_per_gy2=(0.03, 0.03),
        hypoxia_index=(0.20, 0.46) if changed else (0.20, 0.30),
        resistance_index=(0.10, 0.15),
        uncertainty=(0.05, 0.05),
        measurement_quality=quality,
        geometry_qualified=True,
        model_identifiable=True,
    )


def _limits():
    return AdaptationThresholds(
        hypoxia_change=0.10,
        resistance_change=0.10,
        uncertainty_change=0.10,
        anatomy_change_mm=3.0,
        motion_mm=4.0,
        max_uncertainty=0.20,
        min_measurement_quality=0.80,
    )


def _args():
    return {
        "intended_use_id": "SYNTHETIC-LOCKED-HNSCC-A",
        "case_token": "FIXTURE-C01",
        "source_evidence_sha256": SOURCE_DIGEST,
        "previous": _state(0),
        "current": _state(1, changed=True),
        "thresholds": _limits(),
        "last_valid_plan_identity": "LAST-RESEARCH-PLAN",
        "standard_plan_identity": "STANDARD-RESEARCH-PLAN",
    }


def _verify(record, **changes):
    args = _args()
    args.update(changes)
    args.pop("intended_use_id")
    args.pop("case_token")
    return verify_research_decision_audit(record, **args)


def test_audit_replays_deterministically_and_has_no_treatment_authority():
    record = make_research_decision_audit(**_args())
    other = make_research_decision_audit(**_args())
    assert record == other
    assert record.action == "PROPOSE_REOPTIMIZATION"
    assert record.proposal_allowed
    assert record.treatment_authority is False
    assert len(record.audit_sha256) == 64
    assert _verify(record)


def test_source_digest_swap_invalidates_replay():
    record = make_research_decision_audit(**_args())
    assert not _verify(record, source_evidence_sha256=OTHER_DIGEST)


def test_qualification_change_invalidates_replay():
    record = make_research_decision_audit(**_args())
    assert not _verify(record, current=_state(1, changed=True, quality=0.4))


def test_policy_change_invalidates_replay():
    record = make_research_decision_audit(**_args())
    limits = replace(_limits(), max_uncertainty=0.03)
    assert not _verify(record, thresholds=limits)


def test_manual_force_change_invalidates_replay():
    record = make_research_decision_audit(**_args())
    assert not _verify(record, manual_force=True)


def test_record_field_change_is_detected():
    record = make_research_decision_audit(**_args())
    assert not _verify(replace(record, action="HOLD_LAST_VALID"))
    assert not _verify(replace(record, treatment_authority=True))
    assert not _verify(replace(record, proposal_allowed=False))
    assert not _verify(replace(record, audit_sha256=OTHER_DIGEST))


def test_missing_or_malformed_source_digest_is_rejected():
    for bad in ("", "unknown", "f" * 63, "A" * 64):
        with pytest.raises(ValueError, match="SHA-256"):
            make_research_decision_audit(**{**_args(), "source_evidence_sha256": bad})


def test_missing_intended_use_or_case_token_rejected():
    for name in ("case_token", "intended_use_id"):
        with pytest.raises(ValueError, match="identifier"):
            make_research_decision_audit(**{**_args(), name: "  "})


def test_failed_qualification_is_recorded_as_hold_not_treatment():
    args = {**_args(), "current": _state(1, changed=True, quality=0.1)}
    record = make_research_decision_audit(**args)
    assert record.action == "HOLD_LAST_VALID"
    assert record.proposal_allowed is False
    assert record.treatment_authority is False
    assert _verify(record, current=args["current"])


def test_no_trigger_records_no_proposal_and_replays():
    current = _state(1, changed=False)
    record = make_research_decision_audit(**{**_args(), "current": current})
    assert record.action == "NO_ADAPTATION"
    assert record.proposal_allowed is False
    assert _verify(record, current=current)

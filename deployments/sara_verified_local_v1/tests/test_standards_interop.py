from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from worldshepherd_sara.standards_interop import (
    AuthorizationMode,
    CorrelationContract,
    ExpectedOutcome,
    InteropCaseDefinition,
    InteropFixture,
    build_interop_fixture,
    verify_fixture_integrity,
)


CORPUS_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "standards_interop" / "corpus_v0_1.json"


def load_cases() -> list[InteropCaseDefinition]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    assert raw["external_validation_status"] == "NOT_RUN"
    return [InteropCaseDefinition.model_validate(item) for item in raw["cases"]]


def fixtures_by_id() -> dict[str, InteropFixture]:
    return {case.case_id: build_interop_fixture(case) for case in load_cases()}


def test_full_corpus_builds_with_deterministic_evidence_binding():
    cases = load_cases()
    assert len(cases) >= 7
    for case in cases:
        first = build_interop_fixture(case)
        second = build_interop_fixture(case)
        assert verify_fixture_integrity(first)
        assert first.correlation.ws_evidence_digest == second.correlation.ws_evidence_digest
        assert first.external_validation_status == "NOT_RUN"
        assert "no ocsf or gemara certification" in first.claims_boundary.lower()


def test_identifier_grains_remain_distinct():
    fixture = next(iter(fixtures_by_id().values()))
    ids = {
        fixture.correlation.ws_event_uid,
        fixture.correlation.ws_session_uid,
        fixture.correlation.ws_turn_uid,
        fixture.correlation.ws_invocation_uid,
        fixture.correlation.ws_policy_decision_uid,
    }
    assert len(ids) == 5

    with pytest.raises(ValidationError):
        CorrelationContract(
            ws_event_uid="same",
            ws_session_uid="same",
            ws_turn_uid="turn",
            ws_invocation_uid="invocation",
            ws_policy_decision_uid="policy",
            ws_evidence_digest="sha256:" + "0" * 64,
        )


def test_human_and_policy_authorization_are_not_conflated():
    fixtures = fixtures_by_id()
    human = fixtures["INT-REMOTE-HUMAN-ALLOW"]
    policy = fixtures["INT-REMOTE-POLICY-ALLOW"]

    human_auth = human.ocsf_event["actor"]["authorizations"][0]
    policy_auth = policy.ocsf_event["actor"]["authorizations"][0]
    assert human_auth["decision"] == "Approved"
    assert human_auth["worldshepherd_authority_kind"] == "human"
    assert policy_auth["decision"] == "Allowed"
    assert policy_auth["worldshepherd_authority_kind"] == "policy"


def test_denied_action_never_records_execution():
    fixture = fixtures_by_id()["INT-REMOTE-DENY"]
    assert fixture.case.authorization_mode == AuthorizationMode.DENIED
    assert fixture.case.expected_outcome == ExpectedOutcome.DENIED
    assert fixture.ocsf_event["worldshepherd"]["action_executed"] is False
    assert "DENIED_NO_ACTION_EXECUTION" in fixture.expected_flags


def test_hostless_source_does_not_fabricate_device_identity():
    fixture = fixtures_by_id()["INT-FILE-READ-HOSTLESS"]
    assert fixture.case.hostless is True
    assert "device" not in fixture.ocsf_event
    assert "HOSTLESS_SOURCE_NO_FABRICATED_DEVICE" in fixture.expected_flags


def test_declared_readonly_write_behavior_is_flagged():
    fixture = fixtures_by_id()["INT-READONLY-MISMATCH"]
    assert "DECLARED_READONLY_BEHAVIOR_MISMATCH" in fixture.expected_flags
    assert fixture.gemara_evaluation_log["result"] == "Needs Review"


def test_interrupted_action_cannot_silently_report_success():
    fixture = fixtures_by_id()["INT-INTERRUPTED"]
    assert fixture.ocsf_event["status"] == "Interrupted"
    assert fixture.ocsf_event["worldshepherd"]["action_executed"] is False
    assert "INTERRUPTED_EXPLICIT_NON_SUCCESS" in fixture.expected_flags


def test_tampered_ocsf_event_breaks_evidence_chain():
    fixture = fixtures_by_id()["INT-REMOTE-POLICY-ALLOW"]
    payload = fixture.model_dump(mode="json")
    payload["ocsf_event"]["status"] = "Tampered"
    with pytest.raises(ValidationError, match="digest"):
        InteropFixture.model_validate(payload)

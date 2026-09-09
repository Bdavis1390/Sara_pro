from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.autonomy_policy import (
    AutonomyPolicy,
    AutonomousActionCandidate,
    ExecutionDisposition,
)
from worldshepherd_sara.interoperability import InterfaceContract
from worldshepherd_sara.physical_ai_synthetic_adapter import (
    ExternalInterfaceActivation,
    SyntheticMissionAdapter,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "physical_ai_nonkinetic_isr_synthetic_v1.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _adapter() -> tuple[SyntheticMissionAdapter, dict]:
    fixture = _fixture()
    contract = InterfaceContract.model_validate(fixture["contract"])
    return SyntheticMissionAdapter(contract=contract), fixture


def test_fixture_is_explicitly_synthetic_and_not_partner_api_evidence():
    fixture = _fixture()
    assert fixture["claims_state"] == "SIMULATED_ONLY"
    description = fixture["description"].lower()
    assert "not derived from xtend/xos api schemas" in description
    assert "partner-controlled data" in description


def test_ingest_normalizes_contract_events_and_emits_simulation_evidence_only():
    adapter, fixture = _adapter()

    for payload in fixture["events"]:
        observation = adapter.ingest(payload)
        assert observation.accepted is True
        assert observation.duplicate is False
        assert observation.external_command_emitted is False
        assert observation.evidence.external_command_emitted is False
        assert observation.evidence.evidence_scope == "SIMULATION"
        assert observation.evidence.capability_status == "SIMULATED_ONLY"
        assert observation.evidence.event_digest.startswith("sha256:")
        assert observation.evidence.contract_digest == adapter.contract.digest()

    assert "no partner api access" in adapter.claims_boundary().lower()
    assert "platform interoperability" in adapter.claims_boundary().lower()


def test_duplicate_source_event_is_idempotently_rejected_without_command_output():
    adapter, fixture = _adapter()
    payload = fixture["events"][fixture["duplicate_event_index"]]

    first = adapter.ingest(payload)
    second = adapter.ingest(payload)

    assert first.accepted is True
    assert first.duplicate is False
    assert second.accepted is False
    assert second.duplicate is True
    assert second.evidence.evidence_id == first.evidence.evidence_id
    assert second.evidence.event_digest == first.evidence.event_digest
    assert second.external_command_emitted is False


def test_same_event_identity_with_mutated_content_fails_closed():
    adapter, fixture = _adapter()
    payload = fixture["events"][fixture["duplicate_event_index"]]
    adapter.ingest(payload)

    mutated = dict(payload)
    mutated["payload"] = dict(payload["payload"])
    mutated["payload"]["confidence"] = 0.51

    with pytest.raises(ValueError, match="idempotency collision"):
        adapter.ingest(mutated)


def test_contract_rejects_missing_required_payload_field():
    adapter, fixture = _adapter()
    payload = dict(fixture["events"][1])
    payload["payload"] = dict(payload["payload"])
    payload["payload"].pop("confidence")

    with pytest.raises(ValueError, match="missing contracted fields"):
        adapter.ingest(payload)


def test_contract_rejects_unlisted_event_type():
    adapter, fixture = _adapter()
    payload = dict(fixture["events"][0])
    payload["event_id"] = "evt-uncontracted"
    payload["event_type"] = "UNCONTRACTED_PLATFORM_EVENT"

    with pytest.raises(ValueError, match="not allowed by synthetic contract"):
        adapter.ingest(payload)


def test_supervisory_policy_allows_only_bounded_worldshepherd_action_and_emits_no_command():
    adapter, fixture = _adapter()
    policy = AutonomyPolicy.model_validate(fixture["supervisory_policy"])

    annotation = AutonomousActionCandidate(
        action_id="action-annotate-001",
        action_type="ANNOTATE_MISSION",
        confidence=0.99,
        requested_authority=0,
        reversible=True,
        payload={"note": "synthetic operator annotation"},
    )
    result = adapter.evaluate_supervisory_request(candidate=annotation, policy=policy)
    assert result.disposition == ExecutionDisposition.AUTO_ELIGIBLE
    assert result.external_command_emitted is False

    route_override = AutonomousActionCandidate(
        action_id="action-route-override-001",
        action_type="PLATFORM_ROUTE_OVERRIDE",
        confidence=1.0,
        requested_authority=0,
        reversible=True,
    )
    denied = adapter.evaluate_supervisory_request(
        candidate=route_override, policy=policy
    )
    assert denied.disposition == ExecutionDisposition.DENIED
    assert denied.external_command_emitted is False


def test_non_allowlisted_supervisory_action_requires_human_review():
    adapter, fixture = _adapter()
    policy = AutonomyPolicy.model_validate(fixture["supervisory_policy"])
    candidate = AutonomousActionCandidate(
        action_id="action-review-001",
        action_type="CHANGE_SENSOR_TASKING",
        confidence=0.99,
        requested_authority=0,
        reversible=True,
    )

    result = adapter.evaluate_supervisory_request(candidate=candidate, policy=policy)
    assert result.disposition == ExecutionDisposition.HUMAN_REVIEW_REQUIRED
    assert result.external_command_emitted is False


def test_external_activation_requires_authoritative_spec_and_partner_validation():
    with pytest.raises(ValueError, match="authoritative specification"):
        ExternalInterfaceActivation(enabled=True)

    activation = ExternalInterfaceActivation(
        enabled=True,
        authoritative_spec_ref="partner-controlled-spec://approved-interface-v1",
        authoritative_spec_digest="sha256:" + ("0" * 64),
        partner_validation_ref="partner-validation://scope-001",
    )
    contract = InterfaceContract(
        contract_id="SYNTHETIC",
        interface_name="Synthetic",
        version="1",
    )

    with pytest.raises(ValueError, match="synthetic adapter cannot activate"):
        SyntheticMissionAdapter(contract=contract, activation=activation)

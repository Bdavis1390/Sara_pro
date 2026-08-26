from __future__ import annotations

import json
from pathlib import Path

import pytest

from worldshepherd_sara.apnt_adapter import AspnMappingStub, SyntheticPntAdapter
from worldshepherd_sara.apnt_qualification import qualify_synthetic_apnt_timeline
from worldshepherd_sara.common_services import AdapterManifest, MissionEnclaveRegistry, ServiceManifest
from worldshepherd_sara.ddil import Envelope, FaultProfile, apply_fault_profile
from worldshepherd_sara.legacy_normalization import normalize_legacy_corpus
from worldshepherd_sara.prime import ActionProposal, ActionState, decide_action, revoke_action
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
)

ROOT = Path(__file__).resolve().parents[1]


def test_ddil_fault_profile_is_deterministic_and_preserves_fault_evidence():
    messages = [
        Envelope(sequence=i, source="sensor", payload={"value": i}, timestamp_ms=i * 10)
        for i in range(1, 6)
    ]
    profile = FaultProfile(
        drop_sequences=frozenset({2}),
        duplicate_sequences=frozenset({3}),
        stale_sequences=frozenset({4}),
        added_latency_ms=25,
        reorder_windows=((3, 5),),
    )
    first = apply_fault_profile(messages, profile)
    second = apply_fault_profile(messages, profile)
    assert first.replay_signature() == second.replay_signature()
    assert first.dropped == [2]
    assert first.duplicated == [3]
    assert first.stale == [4]
    assert any(item.payload.get("_ws_stale") for item in first.delivered)


def test_apnt_adapter_boundary_fails_closed_for_unimplemented_aspn_mapping():
    synthetic = SyntheticPntAdapter().normalize(
        {
            "source_id": "gnss_primary",
            "source_kind": "GNSS",
            "health": "DEGRADED",
            "confidence": 0.5,
        }
    )
    assert synthetic.source_id == "gnss_primary"
    with pytest.raises(NotImplementedError):
        AspnMappingStub().normalize({})


def test_prime_action_gate_requires_identified_human_decision_and_supports_revocation():
    proposal = ActionProposal(
        proposal_id="APNT-RECOVERY-001",
        action="exclude_gnss",
        rationale=["primary GNSS is untrusted"],
        authority_required="CRE1AWS",
    )
    approved = decide_action(
        proposal,
        reviewer="identified-human-reviewer",
        state=ActionState.APPROVED,
        reason="synthetic exercise approval",
    )
    assert approved.state == ActionState.APPROVED
    revoked = revoke_action(
        approved,
        reviewer="identified-human-reviewer",
        reason="exercise reset",
    )
    assert revoked.state == ActionState.REVOKED


def test_legacy_normalization_preserves_source_identity_without_semantic_inference():
    fixture = json.loads((ROOT / "fixtures" / "mbse_legacy_fixture_v1.json").read_text())
    normalized = normalize_legacy_corpus(fixture["legacy_artifacts"])
    assert len(normalized) == len(fixture["legacy_artifacts"])
    assert {item.source_ref for item in normalized} == {
        f"artifact:{artifact['artifact_id']}" for artifact in fixture["legacy_artifacts"]
    }
    assert all(item.records for item in normalized)


def test_mission_enclave_registry_versions_and_rolls_back_services():
    registry = MissionEnclaveRegistry()
    v1 = ServiceManifest(
        service_id="echo-provenance",
        version="1.0.0",
        interface_version="1",
        software_digest="sha256:v1",
        required_authority="SSPADAWANZZ",
    )
    v2 = v1.model_copy(update={"version": "1.1.0", "software_digest": "sha256:v2"})
    registry.register_service(v1)
    registry.register_service(v2)
    registry.register_adapter(
        AdapterManifest(
            adapter_id="synthetic-apnt",
            platform_family="synthetic",
            interface_version="1",
            software_digest="sha256:adapter",
        )
    )
    assert registry.service("echo-provenance").version == "1.1.0"
    assert registry.rollback_service("echo-provenance").version == "1.0.0"
    assert registry.adapter("synthetic-apnt").validation_state == "UNVALIDATED"


def test_apnt_timeline_compiles_claims_bounded_qualification_bundle():
    fixture = json.loads((ROOT / "fixtures" / "apnt_destroyer_strait_v1.json").read_text())
    requirement = RequirementDeltaRecord(
        requirement_delta_id="PRE-RD-2026-0001",
        demand_class=DemandClass.CONFIRMED_DEMAND,
        source=SourceRecord(
            title="NAVWAR APNT synthetic qualification target",
            agency="NAVWAR",
            url="https://example.invalid/authoritative-source-placeholder",
            solicitation_or_topic="DON26BX05-NP004",
            source_status=SourceStatus.GOVERNMENT_SECONDARY_VERIFIED,
            retrieved_utc="2026-08-26T00:00:00Z",
        ),
        statement="Demonstrate bounded APNT operational-awareness behavior using representative synthetic data.",
        recurrence="Release-5 capture requirement",
        forecast_horizon=ForecastHorizon.D0_90,
        affected_lanes=["APNT", "C2", "mission assurance"],
        existing_capability=["bounded software awareness model"],
        capability_status=[CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        missing_capability=["ASPN/pntOS validation", "Navy operator validation"],
        experiment_or_demonstration_needed=["frozen synthetic scenario"],
        evidence_target=["replayable state/recovery evidence"],
        claims_boundary=["No physical APNT or Navy operational-performance claim"],
    )
    bundle = qualify_synthetic_apnt_timeline(
        fixture=fixture,
        requirement=requirement,
        software_commit="synthetic-test-commit",
        executed_utc="2026-08-26T00:00:00Z",
        operator="pytest",
    )
    assert bundle["capture_ready_source"] is True
    assert bundle["fixture_id"] == "WS-APNT-SYNTH-001"
    assert len(bundle["evidence"]) == len(fixture["timeline"])
    assert all(item["result"] == "PASS" for item in bundle["evidence"])
    assert all(item["evidence_scope"] == "SOFTWARE" for item in bundle["evidence"])
    assert bundle["scope_note"].startswith("Synthetic software qualification")
    assert bundle["prime_action_proposals"]
    assert all(item["state"] == "PROPOSED" for item in bundle["prime_action_proposals"])

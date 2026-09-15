from worldshepherd_sara.improvement_cycle import ImprovementRisk, ImprovementState
from worldshepherd_sara.improvement_routing import ImprovementRoute, route_improvement
from worldshepherd_sara.pre_improvement import pre_to_improvement
from worldshepherd_sara.qualification import (
    CapabilityStatus,
    DemandClass,
    ForecastHorizon,
    RequirementDeltaRecord,
    SourceRecord,
    SourceStatus,
)


def make_requirement(**overrides):
    payload = {
        "requirement_delta_id": "PRE-RD-2026-9001",
        "demand_class": DemandClass.CONFIRMED_DEMAND,
        "source": SourceRecord(
            title="Official requirement source",
            agency="Example Agency",
            url="https://example.gov/requirement",
            solicitation_or_topic="TOPIC-9001",
            source_status=SourceStatus.OFFICIAL_SOURCE_VERIFIED,
            retrieved_utc="2026-09-12T20:40:00Z",
        ),
        "statement": "System must preserve traceable state across degraded connectivity.",
        "recurrence": "Repeated across current and prior requirement sets.",
        "forecast_horizon": ForecastHorizon.D0_90,
        "affected_lanes": ["DDIL", "ECHO"],
        "existing_capability": ["DDIL reconcile", "event provenance"],
        "capability_status": [CapabilityStatus.IMPLEMENTED_IN_SOFTWARE],
        "missing_capability": ["receiving-lane qualification under representative disruption"],
        "experiment_or_demonstration_needed": ["representative DDIL partition/rejoin qualification"],
        "partner_needed": [],
        "evidence_target": ["rejoin integrity PASS", "provenance chain preserved"],
        "likely_future_programs": ["example future program"],
        "claims_boundary": ["No field-performance claim without representative external validation."],
    }
    payload.update(overrides)
    return RequirementDeltaRecord(**payload)


def test_pre_translation_preserves_requirement_lineage_without_maturity_promotion():
    requirement = make_requirement()
    proposal = pre_to_improvement(
        requirement, created_utc="2026-09-12T21:00:00Z"
    )

    assert proposal.state == ImprovementState.PROPOSED
    assert proposal.source_refs[0] == requirement.requirement_delta_id
    assert requirement.source.url in proposal.source_refs
    assert proposal.baseline_capability_status == [CapabilityStatus.IMPLEMENTED_IN_SOFTWARE]
    assert proposal.target_capability_status is None
    assert proposal.generated_by == "PRE->WS-RI"
    assert not proposal.requested_claim_promotion
    assert not proposal.requested_external_execution


def test_pre_translation_turns_missing_capability_and_evidence_targets_into_gates():
    requirement = make_requirement()
    proposal = pre_to_improvement(
        requirement, created_utc="2026-09-12T21:00:00Z"
    )

    assert "receiving-lane qualification" in proposal.proposed_change
    assert "representative DDIL partition/rejoin qualification" in proposal.required_tests
    assert f"{requirement.requirement_delta_id}:source-evidence-gate" in proposal.required_tests
    assert f"{requirement.requirement_delta_id}:claims-boundary-gate" in proposal.required_tests
    assert proposal.success_metrics == ["rejoin integrity PASS", "provenance chain preserved"]


def test_forecast_or_unverified_pre_source_is_high_risk_preparation_not_evidence():
    source = SourceRecord(
        title="Discovery-only source",
        agency="External discovery",
        url="https://example.com/discovery",
        solicitation_or_topic=None,
        source_status=SourceStatus.THIRD_PARTY_DISCOVERY_ONLY,
        retrieved_utc="2026-09-12T20:40:00Z",
    )
    requirement = make_requirement(
        demand_class=DemandClass.WORLDSHEPHERD_FORECAST,
        source=source,
        capability_status=[],
        partner_needed=["representative integration partner"],
    )
    proposal = pre_to_improvement(
        requirement, created_utc="2026-09-12T21:00:00Z"
    )

    assert proposal.baseline_capability_status == [CapabilityStatus.NOT_CURRENTLY_CLAIMED]
    assert proposal.risk_level == ImprovementRisk.HIGH
    assert any("preparation signal only" in risk for risk in proposal.risks)
    assert any("not capture-ready" in risk for risk in proposal.risks)
    assert any("Partner need is unresolved" in risk for risk in proposal.risks)


def test_requirement_delta_routes_back_to_pre_without_execution_authority():
    proposal = pre_to_improvement(
        make_requirement(), created_utc="2026-09-12T21:00:00Z"
    )
    envelope = route_improvement(proposal)

    assert ImprovementRoute.PRE in envelope.routes
    assert ImprovementRoute.ECHO in envelope.routes
    assert ImprovementRoute.OMEGA in envelope.routes
    assert ImprovementRoute.PRIME_TEVV in envelope.routes
    assert ImprovementRoute.CONFIG_CUSTODY not in envelope.routes
    assert not envelope.deployment_authorized
    assert not envelope.external_execution_performed

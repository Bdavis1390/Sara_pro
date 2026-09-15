import pytest

from worldshepherd_sara.config_custody import ConfigurationCustodyLedger, create_snapshot
from worldshepherd_sara.improvement_cycle import (
    ImprovementState,
    apply_assessment,
    assess_improvement,
    record_human_decision,
)
from worldshepherd_sara.improvement_routing import (
    ImprovementRoute,
    build_promoted_configuration_snapshot,
    omega_to_improvement,
    route_improvement,
)
from worldshepherd_sara.qualification import CapabilityStatus, ResultStatus
from worldshepherd_sara.recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    make_seed,
)


def make_node(**overrides):
    payload = {
        "kind": DiscoveryKind.CONTRADICTION,
        "domain": "APNT",
        "statement": "A new source conflicts with the current integration assumption.",
        "source_refs": ["source:official:example"],
        "confidence": 0.82,
        "evidence_state": DiscoveryEvidenceState.CORROBORATED,
        "cross_domain_tags": ["DDIL", "sensor-fusion"],
        "falsification_tests": ["reproduce-conflict", "compare-baseline"],
    }
    payload.update(overrides)
    return make_seed(**payload)


def promote(proposal):
    assessment = assess_improvement(
        proposal,
        {test_id: ResultStatus.PASS for test_id in proposal.required_tests},
    )
    ready = apply_assessment(proposal, assessment)
    assert ready.state == ImprovementState.HUMAN_REVIEW_REQUIRED
    return record_human_decision(
        ready,
        accepted=True,
        reviewer="CRE1AWS",
        reviewed_utc="2026-09-12T20:20:00Z",
        rationale="Required validation passed and bounded configuration staging is authorized.",
        qualification_refs=["WS-QE-2026-9001"],
        authorization_ref="PRIME-AUTH-WSRI-9001",
    )


def test_omega_translation_is_deterministic_and_preserves_lineage():
    node = make_node()
    first = omega_to_improvement(node, created_utc="2026-09-12T20:00:00Z")
    second = omega_to_improvement(node, created_utc="2026-09-12T21:00:00Z")

    assert first.improvement_id == second.improvement_id
    assert first.source_refs[0] == node.node_id
    assert "source:official:example" in first.source_refs
    assert first.generated_by == "WS-OMEGA->WS-RI"
    assert not first.requested_claim_promotion
    assert not first.requested_external_execution


def test_translation_does_not_inflate_capability_maturity():
    unverified = make_node(evidence_state=DiscoveryEvidenceState.UNVERIFIED)
    simulated = make_node(evidence_state=DiscoveryEvidenceState.SIMULATED)

    unverified_proposal = omega_to_improvement(
        unverified, created_utc="2026-09-12T20:00:00Z"
    )
    simulated_proposal = omega_to_improvement(
        simulated, created_utc="2026-09-12T20:00:00Z"
    )

    assert unverified_proposal.baseline_capability_status == [
        CapabilityStatus.NOT_CURRENTLY_CLAIMED
    ]
    assert simulated_proposal.baseline_capability_status == [
        CapabilityStatus.SIMULATED_ONLY
    ]
    assert unverified_proposal.target_capability_status is None
    assert simulated_proposal.target_capability_status is None


def test_translation_requires_evidence_and_red_team_gates():
    node = make_node(falsification_tests=[])
    proposal = omega_to_improvement(node, created_utc="2026-09-12T20:00:00Z")

    assert f"{node.node_id}:source-evidence-gate" in proposal.required_tests
    assert f"{node.node_id}:red-team-gate" in proposal.required_tests


def test_pre_promotion_routing_excludes_configuration_custody():
    proposal = omega_to_improvement(
        make_node(), created_utc="2026-09-12T20:00:00Z"
    )
    envelope = route_improvement(proposal)

    assert ImprovementRoute.ECHO in envelope.routes
    assert ImprovementRoute.OMEGA in envelope.routes
    assert ImprovementRoute.PRIME_TEVV in envelope.routes
    assert ImprovementRoute.PRIME in envelope.routes
    assert ImprovementRoute.OVERWATCH in envelope.routes
    assert ImprovementRoute.RED_TEAM in envelope.routes
    assert ImprovementRoute.CONFIG_CUSTODY not in envelope.routes
    assert not envelope.custody_eligible
    assert not envelope.deployment_authorized
    assert not envelope.external_execution_performed


def test_promoted_routing_becomes_custody_eligible_but_not_deployment_authorized():
    proposal = omega_to_improvement(
        make_node(), created_utc="2026-09-12T20:00:00Z"
    )
    promoted = promote(proposal)
    envelope = route_improvement(promoted)

    assert ImprovementRoute.CONFIG_CUSTODY in envelope.routes
    assert envelope.custody_eligible
    assert not envelope.deployment_authorized
    assert "WS-QE-2026-9001" in envelope.lineage_refs


def test_configuration_snapshot_rejects_unpromoted_improvement():
    proposal = omega_to_improvement(
        make_node(), created_utc="2026-09-12T20:00:00Z"
    )
    with pytest.raises(ValueError):
        build_promoted_configuration_snapshot(
            proposal,
            candidate_payload={"version": 2},
            snapshot_id="cfg-2",
            created_utc="2026-09-12T20:30:00Z",
            actor="CRE1AWS",
            parent_digest=None,
        )


def test_promoted_improvement_stages_appendable_configuration_lineage():
    proposal = omega_to_improvement(
        make_node(), created_utc="2026-09-12T20:00:00Z"
    )
    promoted = promote(proposal)

    ledger = ConfigurationCustodyLedger()
    baseline = create_snapshot(
        snapshot_id="cfg-1",
        payload={"version": 1, "mode": "baseline"},
        created_utc="2026-09-12T19:00:00Z",
        actor="CRE1AWS",
        reason="test baseline",
    )
    ledger.append(baseline)

    candidate = build_promoted_configuration_snapshot(
        promoted,
        candidate_payload={"version": 2, "mode": "candidate"},
        snapshot_id="cfg-2",
        created_utc="2026-09-12T20:30:00Z",
        actor="CRE1AWS",
        parent_digest=baseline.digest,
    )

    assert candidate.parent_digest == baseline.digest
    assert promoted.improvement_id in candidate.reason
    assert "PRIME-AUTH-WSRI-9001" in candidate.reason
    assert "WS-QE-2026-9001" in candidate.reason

    ledger.append(candidate)
    assert ledger.head() == candidate
    assert ledger.verify_chain()

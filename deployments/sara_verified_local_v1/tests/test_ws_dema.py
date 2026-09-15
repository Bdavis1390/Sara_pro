from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldshepherd_sara.cbm_twin import ExpectedEnvelope, TelemetrySample
from worldshepherd_sara.echo_event_store import EchoEventStore
from worldshepherd_sara.prime import ActionState
from worldshepherd_sara.ws_dema import (
    WsDemaScenario,
    rollback_to_baseline,
    run_g1_scenario,
)


def _scenario() -> WsDemaScenario:
    return WsDemaScenario(
        scenario_id="DEMO-001",
        created_utc="2026-09-12T20:00:00+00:00",
        actor="SSPADAWANZZ",
        baseline_configuration={
            "cooling_profile": "nominal",
            "telemetry_period_ms": 100,
            "maintenance_policy": "observe-only",
        },
        candidate_configuration={
            "cooling_profile": "high-margin",
            "telemetry_period_ms": 50,
            "maintenance_policy": "observe-only",
        },
        envelopes=[
            ExpectedEnvelope(metric="power_available_kw", minimum=80.0, maximum=120.0, units="kW"),
            ExpectedEnvelope(metric="coolant_outlet_c", minimum=15.0, maximum=40.0, units="C"),
            ExpectedEnvelope(metric="network_latency_ms", minimum=0.0, maximum=100.0, units="ms"),
        ],
        samples=[
            TelemetrySample(
                sample_id="S1",
                asset_id="power-bus-1",
                metric="power_available_kw",
                value=100.0,
                t_seconds=0,
                source_ref="synthetic://power-bus-1",
            ),
            TelemetrySample(
                sample_id="S2",
                asset_id="cooling-loop-1",
                metric="coolant_outlet_c",
                value=47.0,
                t_seconds=1,
                source_ref="synthetic://cooling-loop-1",
            ),
            TelemetrySample(
                sample_id="S3",
                asset_id="network-link-1",
                metric="network_latency_ms",
                value=25.0,
                t_seconds=2,
                source_ref="synthetic://network-link-1",
            ),
        ],
    )


def test_ws_dema_flags_degraded_health_and_keeps_candidate_proposed_without_human():
    run = run_g1_scenario(_scenario())

    assert run.assessment.readiness == "DEGRADED"
    assert run.assessment.degraded_metrics == ["coolant_outlet_c"]
    assert run.proposal.state == ActionState.PROPOSED
    assert run.active.digest == run.baseline.digest
    assert len(run.ledger.records()) == 1
    assert run.ledger.verify_chain()
    assert run.replay[-1].event_type == "configuration_authorization_state"
    assert run.replay[-1].payload["state"] == "PROPOSED"


def test_ws_dema_human_approval_advances_configuration_and_supports_append_only_rollback():
    run = run_g1_scenario(
        _scenario(),
        reviewer="CRE1AWS",
        approve_candidate=True,
        decision_reason="Approved synthetic G1 configuration change",
    )

    assert run.proposal.state == ActionState.APPROVED
    assert run.active.payload["cooling_profile"] == "high-margin"
    assert run.active.digest != run.baseline.digest
    assert len(run.ledger.records()) == 2
    assert run.ledger.verify_chain()

    rollback = rollback_to_baseline(
        run,
        snapshot_id="DEMO-001-rollback",
        created_utc="2026-09-12T20:05:00+00:00",
        actor="CRE1AWS",
        reason="Synthetic rollback drill",
    )
    assert rollback.payload == run.baseline.payload
    assert rollback.parent_digest == run.active.digest
    assert len(run.ledger.records()) == 3
    assert run.ledger.verify_chain()


def test_ws_dema_audit_records_are_echo_compatible_and_deduplicate(tmp_path):
    run = run_g1_scenario(_scenario())
    store = EchoEventStore(tmp_path / "echo")

    outcomes = [store.ingest(record).outcome for record in run.audit_records]
    assert set(outcomes) == {"STORED"}
    assert store.health()["ok"] is True

    replayed = store.ingest(run.audit_records[0])
    assert replayed.outcome == "DEDUPLICATED"
    assert replayed.record.delivery_count == 2


def test_ws_dema_rejects_weapon_control_fields_from_g1_configuration():
    with pytest.raises(ValidationError, match="prohibits weapon-control field"):
        WsDemaScenario(
            scenario_id="UNSAFE-001",
            created_utc="2026-09-12T20:00:00+00:00",
            actor="SSPADAWANZZ",
            baseline_configuration={"mode": "observe-only"},
            candidate_configuration={"target_id": "not-allowed"},
            envelopes=[ExpectedEnvelope(metric="temperature_c", minimum=0, maximum=100)],
            samples=[
                TelemetrySample(
                    sample_id="S1",
                    asset_id="thermal-proxy-1",
                    metric="temperature_c",
                    value=25,
                    t_seconds=0,
                    source_ref="synthetic://thermal-proxy-1",
                )
            ],
        )

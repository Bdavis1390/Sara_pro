from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.echo_event_store import EchoEventConflict, EchoEventStore
from worldshepherd_sara.sda import (
    SdaContractValidationState,
    SdaIngestDisposition,
    SdaInterfaceContract,
    SdaObservation,
    SdaSourceClass,
    SdaSourceIdentity,
    evaluate_sda_ingest,
    fuse_sda_state_vectors,
    sda_audit_record,
    sda_fusion_evidence_graph,
)


EPOCH = datetime(2026, 9, 17, 23, 0, tzinfo=timezone.utc)
RAW_DIGEST = "sha256:" + "a" * 64
SPEC_DIGEST = "sha256:" + "b" * 64


def covariance(position_variance: float = 1.0, velocity_variance: float = 0.01):
    matrix = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(3):
        matrix[index][index] = position_variance
    for index in range(3, 6):
        matrix[index][index] = velocity_variance
    return matrix


def contract(**overrides) -> SdaInterfaceContract:
    values = {
        "contract_id": "SDA-CONTRACT-SYNTH-001",
        "source_id": "SYNTH-RADAR-A",
        "adapter_id": "WS-SDA-SYNTH",
        "adapter_version": "1.0.0",
        "authoritative_spec_ref": "internal://ws-sda/synthetic-contract-v1",
        "authoritative_spec_digest": SPEC_DIGEST,
        "allowed_reference_frames": ["GCRF"],
        "allowed_releasability_tags": ["US_ONLY", "PARTNER_TEST"],
        "max_age_seconds": 600.0,
        "max_future_skew_seconds": 30.0,
        "max_clock_uncertainty_seconds": 0.05,
        "validation_state": SdaContractValidationState.SYNTHETIC,
        "validation_ref": "test://sda-contract-validation",
        "enabled": True,
    }
    values.update(overrides)
    return SdaInterfaceContract.model_validate(values)


def observation(
    active_contract: SdaInterfaceContract,
    *,
    observation_id: str = "OBS-001",
    source_event_id: str = "EVENT-001",
    source_sequence: int = 1,
    source_id: str = "SYNTH-RADAR-A",
    adapter_id: str = "WS-SDA-SYNTH",
    adapter_version: str = "1.0.0",
    observed_at: datetime = EPOCH,
    received_at: datetime = EPOCH + timedelta(seconds=1),
    reference_frame: str = "GCRF",
    position_km: tuple[float, float, float] = (1000.0, 2000.0, 3000.0),
    velocity_km_s: tuple[float, float, float] = (1.0, 2.0, 3.0),
    covariance_6x6=None,
    measurement_confidence: float = 0.8,
    source_reliability: float = 0.7,
    releasability_tags=None,
    raw_source_digest: str = RAW_DIGEST,
) -> SdaObservation:
    return SdaObservation(
        observation_id=observation_id,
        source_event_id=source_event_id,
        source_sequence=source_sequence,
        source=SdaSourceIdentity(
            source_id=source_id,
            source_class=SdaSourceClass.SYNTHETIC,
            provider="Worldshepherd synthetic fixture",
            sensor_id="SYNTH-SENSOR-1",
            adapter_id=adapter_id,
            adapter_version=adapter_version,
        ),
        observed_at=observed_at,
        received_at=received_at,
        time_system="UTC",
        clock_uncertainty_seconds=0.01,
        reference_frame=reference_frame,
        position_km=position_km,
        velocity_km_s=velocity_km_s,
        covariance_6x6=covariance_6x6 or covariance(),
        measurement_confidence=measurement_confidence,
        source_reliability=source_reliability,
        handling_label="UNCLASSIFIED_SYNTHETIC",
        releasability_tags=list(releasability_tags or ["US_ONLY"]),
        raw_source_digest=raw_source_digest,
        interface_contract_id=active_contract.contract_id,
        interface_contract_digest=active_contract.digest(),
        transformation_refs=["adapter:synthetic-v1"],
    )


def test_observation_schema_rejects_unknown_fields_and_bad_covariance():
    active = contract()
    payload = observation(active).model_dump(mode="json")
    payload["unexpected"] = True
    with pytest.raises(ValidationError):
        SdaObservation.model_validate(payload)

    bad = covariance()
    bad[0][1] = 1.0
    with pytest.raises(ValidationError, match="symmetric"):
        observation(active, covariance_6x6=bad)


def test_contract_fails_closed_if_enabled_without_validation_reference():
    with pytest.raises(ValidationError, match="validation_ref"):
        contract(validation_ref=None)


def test_semantic_digest_changes_when_safe_canonical_measurement_changes():
    active = contract()
    first = observation(active)
    second = observation(active, position_km=(1001.0, 2000.0, 3000.0))
    assert first.stable_event_id() == second.stable_event_id()
    assert first.semantic_digest() != second.semantic_digest()


def test_fresh_observation_is_accepted_and_advances_replay_state():
    active = contract()
    item = observation(active)
    result = evaluate_sda_ingest(item, contract=active, now=EPOCH + timedelta(seconds=5))

    assert result.disposition == SdaIngestDisposition.ACCEPT
    assert result.next_replay_state is not None
    assert result.next_replay_state.last_sequence == 1
    assert result.next_replay_state.last_event_id == "EVENT-001"


def test_exact_replay_is_duplicate_but_mutated_same_sequence_is_rejected():
    active = contract()
    item = observation(active)
    accepted = evaluate_sda_ingest(item, contract=active, now=EPOCH + timedelta(seconds=5))
    assert accepted.next_replay_state is not None

    duplicate = evaluate_sda_ingest(
        item,
        contract=active,
        replay_state=accepted.next_replay_state,
        now=EPOCH + timedelta(seconds=5),
    )
    assert duplicate.disposition == SdaIngestDisposition.DUPLICATE

    mutated = observation(active, position_km=(9999.0, 2000.0, 3000.0))
    rejected = evaluate_sda_ingest(
        mutated,
        contract=active,
        replay_state=accepted.next_replay_state,
        now=EPOCH + timedelta(seconds=5),
    )
    assert rejected.disposition == SdaIngestDisposition.REJECT
    assert any("collision" in reason for reason in rejected.reasons)


def test_backward_sequence_source_identity_and_stale_contract_digest_fail_closed():
    active = contract()
    initial = observation(active, source_sequence=10, source_event_id="EVENT-010")
    accepted = evaluate_sda_ingest(initial, contract=active, now=EPOCH + timedelta(seconds=5))
    assert accepted.next_replay_state is not None

    backward = observation(
        active,
        observation_id="OBS-009",
        source_event_id="EVENT-009",
        source_sequence=9,
    )
    back_result = evaluate_sda_ingest(
        backward,
        contract=active,
        replay_state=accepted.next_replay_state,
        now=EPOCH + timedelta(seconds=5),
    )
    assert back_result.disposition == SdaIngestDisposition.REJECT

    wrong_source = observation(active, source_id="SPOOFED-SOURCE")
    source_result = evaluate_sda_ingest(
        wrong_source, contract=active, now=EPOCH + timedelta(seconds=5)
    )
    assert source_result.disposition == SdaIngestDisposition.REJECT

    payload = observation(active).model_dump(mode="json")
    payload["interface_contract_digest"] = "sha256:" + "c" * 64
    stale_contract = SdaObservation.model_validate(payload)
    digest_result = evaluate_sda_ingest(
        stale_contract, contract=active, now=EPOCH + timedelta(seconds=5)
    )
    assert digest_result.disposition == SdaIngestDisposition.REJECT


def test_stale_future_clock_frame_and_releasability_conditions_quarantine():
    active = contract()

    stale = observation(active, observed_at=EPOCH - timedelta(seconds=1000))
    assert evaluate_sda_ingest(
        stale, contract=active, now=EPOCH
    ).disposition == SdaIngestDisposition.QUARANTINE

    future = observation(active, observed_at=EPOCH + timedelta(seconds=31))
    assert evaluate_sda_ingest(
        future, contract=active, now=EPOCH
    ).disposition == SdaIngestDisposition.QUARANTINE

    wrong_frame = observation(active, reference_frame="TEME")
    assert evaluate_sda_ingest(
        wrong_frame, contract=active, now=EPOCH + timedelta(seconds=5)
    ).disposition == SdaIngestDisposition.QUARANTINE

    restricted = observation(active, releasability_tags=["NOT-IN-CONTRACT"])
    assert evaluate_sda_ingest(
        restricted, contract=active, now=EPOCH + timedelta(seconds=5)
    ).disposition == SdaIngestDisposition.QUARANTINE

    payload = observation(active).model_dump(mode="json")
    payload["clock_uncertainty_seconds"] = 0.5
    poor_clock = SdaObservation.model_validate(payload)
    assert evaluate_sda_ingest(
        poor_clock, contract=active, now=EPOCH + timedelta(seconds=5)
    ).disposition == SdaIngestDisposition.QUARANTINE


def test_echo_store_deduplicates_exact_event_and_detects_semantic_conflict(tmp_path):
    active = contract()
    first = observation(active)
    first_result = evaluate_sda_ingest(first, contract=active, now=EPOCH + timedelta(seconds=5))
    record = sda_audit_record(first, first_result)

    echo = EchoEventStore(tmp_path / "echo-sda")
    stored = echo.ingest(record)
    deduplicated = echo.ingest(record)
    assert stored.outcome == "STORED"
    assert deduplicated.outcome == "DEDUPLICATED"

    mutated = observation(active, position_km=(1000.5, 2000.0, 3000.0))
    mutated_result = evaluate_sda_ingest(
        mutated, contract=active, now=EPOCH + timedelta(seconds=5)
    )
    assert mutated_result.event_id == first_result.event_id
    with pytest.raises(EchoEventConflict):
        echo.ingest(sda_audit_record(mutated, mutated_result))


def test_inverse_variance_fusion_preserves_lineage_and_ignores_governance_scores_as_weights():
    active = contract()
    first = observation(
        active,
        observation_id="OBS-A",
        source_event_id="EVENT-A",
        source_sequence=1,
        position_km=(0.0, 0.0, 0.0),
        velocity_km_s=(0.0, 0.0, 0.0),
        covariance_6x6=covariance(position_variance=4.0, velocity_variance=4.0),
        measurement_confidence=0.1,
        source_reliability=0.1,
    )
    second = observation(
        active,
        observation_id="OBS-B",
        source_event_id="EVENT-B",
        source_sequence=2,
        position_km=(10.0, 10.0, 10.0),
        velocity_km_s=(10.0, 10.0, 10.0),
        covariance_6x6=covariance(position_variance=1.0, velocity_variance=1.0),
        measurement_confidence=0.9,
        source_reliability=0.9,
    )
    fused = fuse_sda_state_vectors([first, second], conflict_threshold=1000.0)
    assert fused.position_km == pytest.approx((8.0, 8.0, 8.0))
    assert fused.velocity_km_s == pytest.approx((8.0, 8.0, 8.0))
    assert fused.covariance_6x6[0][0] == pytest.approx(0.8)
    assert fused.source_observation_ids == ["OBS-A", "OBS-B"]

    first_scores_changed = first.model_copy(
        update={"measurement_confidence": 1.0, "source_reliability": 1.0}
    )
    second_scores_changed = second.model_copy(
        update={"measurement_confidence": 0.0, "source_reliability": 0.0}
    )
    rescored = fuse_sda_state_vectors(
        [first_scores_changed, second_scores_changed],
        conflict_threshold=1000.0,
    )
    assert rescored.position_km == fused.position_km
    assert rescored.velocity_km_s == fused.velocity_km_s


def test_conflict_is_explicit_and_evidence_graph_retains_every_source():
    active = contract()
    first = observation(
        active,
        observation_id="OBS-A",
        source_event_id="EVENT-A",
        source_sequence=1,
        position_km=(0.0, 0.0, 0.0),
        velocity_km_s=(0.0, 0.0, 0.0),
        covariance_6x6=covariance(position_variance=1.0, velocity_variance=1.0),
    )
    second = observation(
        active,
        observation_id="OBS-B",
        source_event_id="EVENT-B",
        source_sequence=2,
        position_km=(100.0, 100.0, 100.0),
        velocity_km_s=(10.0, 10.0, 10.0),
        covariance_6x6=covariance(position_variance=1.0, velocity_variance=1.0),
    )

    fused = fuse_sda_state_vectors([first, second], conflict_threshold=36.0)
    assert len(fused.conflicts) == 1
    graph = sda_fusion_evidence_graph(
        graph_id="WS-SDA-GRAPH-TEST",
        observations=[first, second],
        hypothesis=fused,
    )

    node_ids = {node.node_id for node in graph.nodes}
    assert "sda-observation:OBS-A" in node_ids
    assert "sda-observation:OBS-B" in node_ids
    assert f"sda-hypothesis:{fused.hypothesis_id}" in node_ids
    assert {edge.relation for edge in graph.edges} >= {
        "contributes_to",
        "conflicts_in_fusion",
        "qualifies_uncertainty",
    }

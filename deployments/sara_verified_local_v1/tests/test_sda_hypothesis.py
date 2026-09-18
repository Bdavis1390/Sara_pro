from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worldshepherd_sara.sda import SdaSourceClass, SdaSourceIdentity
from worldshepherd_sara.sda_canonical import (
    SdaCanonicalEnvelope,
    SdaCanonicalStateVector,
    SdaCanonicalTimeTag,
    SdaObjectIdentity,
)
from worldshepherd_sara.sda_hypothesis import (
    SdaHypothesisError,
    build_state_hypothesis_set,
    sda_hypothesis_evidence_graph,
)


NOW = datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)


def covariance(position_variance: float = 1.0, velocity_variance: float = 1.0):
    matrix = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(3):
        matrix[index][index] = position_variance
    for index in range(3, 6):
        matrix[index][index] = velocity_variance
    return matrix


def envelope(
    observation_id: str,
    x_km: float,
    *,
    object_id: str = "2026-999A",
    center_name: str = "EARTH",
    reference_frame: str = "GCRF",
    covariance_reference_frame: str = "GCRF",
    epoch: str = "2026-09-18T01:00:00",
    covariance_matrix=None,
    source_id: str | None = None,
) -> SdaCanonicalEnvelope:
    return SdaCanonicalEnvelope(
        observation_id=observation_id,
        source_event_id=f"EVENT-{observation_id}",
        source_sequence=int(observation_id.rsplit("-", 1)[-1]),
        source=SdaSourceIdentity(
            source_id=source_id or f"SOURCE-{observation_id}",
            source_class=SdaSourceClass.SYNTHETIC,
            provider="Worldshepherd synthetic G5 fixture",
            sensor_id=f"SENSOR-{observation_id}",
            adapter_id="WS-SDA-G5-TEST",
            adapter_version="1.0.0",
        ),
        object_identity=SdaObjectIdentity(
            object_id=object_id,
            object_name="WS-SYNTH-OBJECT",
            center_name=center_name,
        ),
        time_tag=SdaCanonicalTimeTag(
            raw=epoch,
            time_system="UTC",
            normalized_utc=NOW,
        ),
        received_at=NOW,
        payload=SdaCanonicalStateVector(
            reference_frame=reference_frame,
            position_km=(x_km, 0.0, 0.0),
            velocity_km_s=(0.0, 0.0, 0.0),
            covariance_6x6=covariance_matrix
            if covariance_matrix is not None
            else covariance(),
            covariance_reference_frame=covariance_reference_frame,
            covariance_source_ref="fixture:G5-covariance",
        ),
        raw_source_digest="sha256:" + observation_id[-1].lower() * 64,
        interface_contract_id="G5-SYNTH-CONTRACT",
        interface_contract_digest="sha256:" + "e" * 64,
        source_standard="WS-SYNTHETIC-G5",
        source_profile="WS-SDA-G5-TEST",
        source_message_id=f"MSG-{observation_id}",
        transformation_refs=["fixture:G5"],
    )


def test_all_compatible_observations_form_one_hypothesis():
    a = envelope("OBS-1", 0.0)
    b = envelope("OBS-2", 2.0)

    result = build_state_hypothesis_set([b, a], compatibility_threshold=36.0)

    assert result.requires_resolution is False
    assert result.automatic_winner_selected is False
    assert len(result.hypotheses) == 1
    hypothesis = result.hypotheses[0]
    assert hypothesis.support_observation_ids == ["OBS-1", "OBS-2"]
    assert hypothesis.position_km[0] == pytest.approx(1.0)
    assert hypothesis.covariance_6x6[0][0] == pytest.approx(0.5)
    assert hypothesis.conflicting_observation_ids == []


def test_outlier_is_retained_as_alternative_hypothesis_not_averaged_away():
    a = envelope("OBS-1", 0.0)
    b = envelope("OBS-2", 2.0)
    c = envelope("OBS-3", 100.0)

    result = build_state_hypothesis_set([a, b, c], compatibility_threshold=36.0)

    support_sets = {tuple(item.support_observation_ids) for item in result.hypotheses}
    assert support_sets == {("OBS-1", "OBS-2"), ("OBS-3",)}
    assert result.requires_resolution is True
    assert result.automatic_winner_selected is False

    ab = next(item for item in result.hypotheses if len(item.support_observation_ids) == 2)
    outlier = next(item for item in result.hypotheses if item.support_observation_ids == ["OBS-3"])
    assert ab.conflicting_observation_ids == ["OBS-3"]
    assert outlier.conflicting_observation_ids == ["OBS-1", "OBS-2"]


def test_bridge_case_retains_overlapping_maximal_hypotheses():
    a = envelope("OBS-1", 0.0)
    b = envelope("OBS-2", 5.0)
    c = envelope("OBS-3", 10.0)

    result = build_state_hypothesis_set([a, b, c], compatibility_threshold=36.0)

    support_sets = {tuple(item.support_observation_ids) for item in result.hypotheses}
    assert support_sets == {("OBS-1", "OBS-2"), ("OBS-2", "OBS-3")}
    assert result.requires_resolution is True

    residuals = {
        (item.left_observation_id, item.right_observation_id): item
        for item in result.pairwise_residuals
    }
    assert residuals[("OBS-1", "OBS-2")].compatible is True
    assert residuals[("OBS-2", "OBS-3")].compatible is True
    assert residuals[("OBS-1", "OBS-3")].compatible is False


@pytest.mark.parametrize(
    "items, match",
    [
        ([envelope("OBS-1", 0.0), envelope("OBS-2", 0.0, object_id="OTHER")], "object/center"),
        ([envelope("OBS-1", 0.0), envelope("OBS-2", 0.0, center_name="MARS")], "object/center"),
        ([envelope("OBS-1", 0.0), envelope("OBS-2", 0.0, reference_frame="ITRF2000", covariance_reference_frame="ITRF2000")], "reference frame"),
        ([envelope("OBS-1", 0.0), envelope("OBS-2", 0.0, epoch="2026-09-18T01:00:01")], "identical raw epoch"),
    ],
)
def test_reference_fusion_refuses_identity_frame_and_epoch_mismatch(items, match):
    with pytest.raises(SdaHypothesisError, match=match):
        build_state_hypothesis_set(items)


def test_missing_covariance_and_covariance_frame_mismatch_fail_closed():
    no_cov = envelope("OBS-1", 0.0).model_copy(
        update={
            "payload": SdaCanonicalStateVector(
                reference_frame="GCRF",
                position_km=(0.0, 0.0, 0.0),
                velocity_km_s=(0.0, 0.0, 0.0),
            )
        }
    )
    with pytest.raises(SdaHypothesisError, match="lacks covariance"):
        build_state_hypothesis_set([no_cov])

    mismatch = envelope(
        "OBS-1",
        0.0,
        covariance_reference_frame="RTN",
    )
    with pytest.raises(SdaHypothesisError, match="covariance frame differs"):
        build_state_hypothesis_set([mismatch])


def test_zero_variance_is_not_silently_promoted_to_infinite_weight():
    zero = covariance()
    zero[0][0] = 0.0
    item = envelope("OBS-1", 0.0, covariance_matrix=zero)

    with pytest.raises(SdaHypothesisError, match="non-positive fusion variance"):
        build_state_hypothesis_set([item])


def test_hypothesis_graph_preserves_support_and_conflict_edges():
    a = envelope("OBS-1", 0.0)
    b = envelope("OBS-2", 2.0)
    c = envelope("OBS-3", 100.0)
    result = build_state_hypothesis_set([a, b, c], compatibility_threshold=36.0)

    graph = sda_hypothesis_evidence_graph(
        graph_id="WS-SDA-G5-GRAPH-TEST",
        observations=[a, b, c],
        hypothesis_set=result,
    )

    relations = {edge.relation for edge in graph.edges}
    assert "supports_hypothesis" in relations
    assert "conflicts_with_hypothesis" in relations
    observation_nodes = {
        node.node_id for node in graph.nodes if node.node_type == "sda_canonical_state_evidence"
    }
    assert observation_nodes == {
        "sda-canonical:OBS-1",
        "sda-canonical:OBS-2",
        "sda-canonical:OBS-3",
    }


def test_input_count_is_bounded_and_duplicate_ids_are_rejected():
    too_many = [
        envelope(f"OBS-{index}", float(index))
        for index in range(1, 14)
    ]
    with pytest.raises(SdaHypothesisError, match="at most 12"):
        build_state_hypothesis_set(too_many)

    duplicate = envelope("OBS-1", 0.0)
    with pytest.raises(SdaHypothesisError, match="IDs must be unique"):
        build_state_hypothesis_set([duplicate, duplicate])


def test_claims_boundary_explicitly_excludes_targeting_and_winner_selection():
    a = envelope("OBS-1", 0.0)
    c = envelope("OBS-2", 100.0)
    result = build_state_hypothesis_set([a, c], compatibility_threshold=36.0)

    assert result.automatic_winner_selected is False
    for hypothesis in result.hypotheses:
        boundary = hypothesis.claims_boundary.lower()
        assert "targeting" in boundary
        assert "weapon-cue" in boundary

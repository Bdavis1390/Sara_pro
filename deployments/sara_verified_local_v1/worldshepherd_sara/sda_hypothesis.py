from __future__ import annotations

import math
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode, canonical_digest
from .sda_canonical import (
    SdaCanonicalEnvelope,
    SdaCanonicalStateVector,
    SdaObjectIdentity,
)


MAX_G5_OBSERVATIONS = 12
MAX_G5_HYPOTHESES = 64


class SdaHypothesisError(ValueError):
    pass


class SdaPairwiseResidual(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_observation_id: str
    right_observation_id: str
    normalized_residual_score: float = Field(ge=0.0)
    threshold: float = Field(gt=0.0)
    compatible: bool


class SdaStateHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str = Field(pattern=r"^SDA-HYP-[0-9a-f]{16}$")
    object_identity: SdaObjectIdentity
    time_system: str = Field(min_length=1)
    time_raw: str = Field(min_length=1)
    reference_frame: str = Field(min_length=1)
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    covariance_6x6: list[list[float]]
    support_observation_ids: list[str] = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)
    conflicting_observation_ids: list[str] = Field(default_factory=list)
    method: str = (
        "pairwise-compatible maximal-clique hypothesis with diagonal "
        "inverse-variance state fusion"
    )
    claims_boundary: str = (
        "Same-object, same-epoch, same-frame reference fusion only. No orbit "
        "propagation, maneuver detection, association across unknown identities, "
        "operational tracking, targeting, or weapon-cue generation."
    )

    @model_validator(mode="after")
    def ids_are_disjoint_and_unique(self):
        support = set(self.support_observation_ids)
        conflicts = set(self.conflicting_observation_ids)
        if len(support) != len(self.support_observation_ids):
            raise ValueError("support_observation_ids contains duplicates")
        if len(conflicts) != len(self.conflicting_observation_ids):
            raise ValueError("conflicting_observation_ids contains duplicates")
        if support & conflicts:
            raise ValueError("support and conflicting observation IDs must be disjoint")
        return self


class SdaHypothesisSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    set_id: str = Field(pattern=r"^SDA-HYPSET-[0-9a-f]{16}$")
    object_identity: SdaObjectIdentity
    time_system: str
    time_raw: str
    reference_frame: str
    hypotheses: list[SdaStateHypothesis] = Field(min_length=1)
    pairwise_residuals: list[SdaPairwiseResidual] = Field(default_factory=list)
    requires_resolution: bool
    automatic_winner_selected: bool = False
    claims_boundary: str = (
        "Alternative hypotheses are retained when measurements are mutually "
        "incompatible. This reference layer does not automatically select an "
        "operational winner or produce consequential control actions."
    )

    @model_validator(mode="after")
    def resolution_flag_matches_hypothesis_count(self):
        if self.requires_resolution != (len(self.hypotheses) > 1):
            raise ValueError("requires_resolution must reflect hypothesis count")
        if self.automatic_winner_selected:
            raise ValueError("G5 reference profile forbids automatic winner selection")
        return self


def _state(envelope: SdaCanonicalEnvelope) -> SdaCanonicalStateVector:
    if not isinstance(envelope.payload, SdaCanonicalStateVector):
        raise SdaHypothesisError(
            f"observation {envelope.observation_id} is not a state-vector payload"
        )
    return envelope.payload


def _identity_key(envelope: SdaCanonicalEnvelope) -> tuple[str, str | None]:
    if envelope.object_identity is None:
        raise SdaHypothesisError(
            f"observation {envelope.observation_id} lacks object identity"
        )
    return (
        envelope.object_identity.object_id,
        envelope.object_identity.center_name,
    )


def _time_key(envelope: SdaCanonicalEnvelope) -> tuple[str, str]:
    return (envelope.time_tag.time_system, envelope.time_tag.raw)


def _validate_observations(
    observations: list[SdaCanonicalEnvelope],
) -> tuple[SdaObjectIdentity, str, str, str]:
    if not observations:
        raise SdaHypothesisError("G5 requires at least one observation")
    if len(observations) > MAX_G5_OBSERVATIONS:
        raise SdaHypothesisError(
            f"G5 reference profile accepts at most {MAX_G5_OBSERVATIONS} observations"
        )

    ids = [item.observation_id for item in observations]
    if len(ids) != len(set(ids)):
        raise SdaHypothesisError("observation IDs must be unique")

    object_keys = {_identity_key(item) for item in observations}
    if len(object_keys) != 1:
        raise SdaHypothesisError(
            "G5 reference fusion requires one explicit object/center identity"
        )

    time_keys = {_time_key(item) for item in observations}
    if len(time_keys) != 1:
        raise SdaHypothesisError(
            "G5 reference fusion requires an identical raw epoch and time system"
        )

    frames: set[str] = set()
    for item in observations:
        state = _state(item)
        frames.add(state.reference_frame)
        if state.covariance_6x6 is None:
            raise SdaHypothesisError(
                f"observation {item.observation_id} lacks covariance"
            )
        if state.covariance_reference_frame != state.reference_frame:
            raise SdaHypothesisError(
                f"observation {item.observation_id} covariance frame differs from state frame"
            )
        for index in range(6):
            if state.covariance_6x6[index][index] <= 0.0:
                raise SdaHypothesisError(
                    f"observation {item.observation_id} has non-positive fusion variance"
                )

    if len(frames) != 1:
        raise SdaHypothesisError(
            "G5 reference fusion requires one state/covariance reference frame"
        )

    first = observations[0]
    assert first.object_identity is not None
    time_system, time_raw = _time_key(first)
    return first.object_identity, time_system, time_raw, _state(first).reference_frame


def _components(envelope: SdaCanonicalEnvelope) -> tuple[float, ...]:
    state = _state(envelope)
    return (*state.position_km, *state.velocity_km_s)


def _residual_score(
    left: SdaCanonicalEnvelope,
    right: SdaCanonicalEnvelope,
) -> float:
    left_state = _state(left)
    right_state = _state(right)
    assert left_state.covariance_6x6 is not None
    assert right_state.covariance_6x6 is not None

    score = 0.0
    left_components = _components(left)
    right_components = _components(right)
    for index in range(6):
        variance = (
            left_state.covariance_6x6[index][index]
            + right_state.covariance_6x6[index][index]
        )
        if variance <= 0.0 or not math.isfinite(variance):
            raise SdaHypothesisError("pairwise residual denominator is invalid")
        delta = left_components[index] - right_components[index]
        score += (delta * delta) / variance
    if not math.isfinite(score):
        raise SdaHypothesisError("pairwise residual score is non-finite")
    return score


def _maximal_compatible_cliques(
    observation_ids: list[str],
    neighbors: dict[str, set[str]],
) -> list[tuple[str, ...]]:
    cliques: list[tuple[str, ...]] = []

    def bron_kerbosch(
        current: set[str],
        candidates: set[str],
        excluded: set[str],
    ) -> None:
        if not candidates and not excluded:
            cliques.append(tuple(sorted(current)))
            if len(cliques) > MAX_G5_HYPOTHESES:
                raise SdaHypothesisError(
                    f"G5 hypothesis count exceeds {MAX_G5_HYPOTHESES}"
                )
            return

        for vertex in sorted(list(candidates)):
            bron_kerbosch(
                current | {vertex},
                candidates & neighbors[vertex],
                excluded & neighbors[vertex],
            )
            candidates.remove(vertex)
            excluded.add(vertex)

    bron_kerbosch(set(), set(observation_ids), set())
    return sorted(set(cliques), key=lambda item: (-len(item), item))


def _fuse_clique(
    clique: tuple[str, ...],
    *,
    by_id: dict[str, SdaCanonicalEnvelope],
    object_identity: SdaObjectIdentity,
    time_system: str,
    time_raw: str,
    reference_frame: str,
    all_observation_ids: set[str],
) -> SdaStateHypothesis:
    members = [by_id[item] for item in clique]

    fused: list[float] = []
    variances: list[float] = []
    for index in range(6):
        values: list[float] = []
        weights: list[float] = []
        for observation in members:
            state = _state(observation)
            assert state.covariance_6x6 is not None
            variance = state.covariance_6x6[index][index]
            values.append(_components(observation)[index])
            weights.append(1.0 / variance)
        total_weight = sum(weights)
        fused.append(
            sum(value * weight for value, weight in zip(values, weights))
            / total_weight
        )
        variances.append(1.0 / total_weight)

    covariance = [[0.0 for _ in range(6)] for _ in range(6)]
    for index, variance in enumerate(variances):
        covariance[index][index] = variance

    source_ids = sorted({item.source.source_id for item in members})
    conflicts = sorted(all_observation_ids - set(clique))
    identity_document = {
        "object_identity": object_identity.model_dump(mode="json"),
        "time_system": time_system,
        "time_raw": time_raw,
        "reference_frame": reference_frame,
        "support_observation_ids": list(clique),
        "source_ids": source_ids,
        "position_km": fused[:3],
        "velocity_km_s": fused[3:],
        "covariance_6x6": covariance,
    }
    suffix = canonical_digest(identity_document).split(":", 1)[1][:16]

    return SdaStateHypothesis(
        hypothesis_id=f"SDA-HYP-{suffix}",
        object_identity=object_identity,
        time_system=time_system,
        time_raw=time_raw,
        reference_frame=reference_frame,
        position_km=(fused[0], fused[1], fused[2]),
        velocity_km_s=(fused[3], fused[4], fused[5]),
        covariance_6x6=covariance,
        support_observation_ids=list(clique),
        source_ids=source_ids,
        conflicting_observation_ids=conflicts,
    )


def build_state_hypothesis_set(
    observations: Iterable[SdaCanonicalEnvelope],
    *,
    compatibility_threshold: float = 36.0,
) -> SdaHypothesisSet:
    ordered = sorted(list(observations), key=lambda item: item.observation_id)
    if compatibility_threshold <= 0.0 or not math.isfinite(compatibility_threshold):
        raise SdaHypothesisError("compatibility_threshold must be finite and positive")

    object_identity, time_system, time_raw, reference_frame = _validate_observations(
        ordered
    )
    by_id = {item.observation_id: item for item in ordered}
    observation_ids = list(by_id)
    neighbors = {item: set() for item in observation_ids}
    residuals: list[SdaPairwiseResidual] = []

    for left_index, left_id in enumerate(observation_ids):
        for right_id in observation_ids[left_index + 1 :]:
            score = _residual_score(by_id[left_id], by_id[right_id])
            compatible = score <= compatibility_threshold
            residuals.append(
                SdaPairwiseResidual(
                    left_observation_id=left_id,
                    right_observation_id=right_id,
                    normalized_residual_score=score,
                    threshold=compatibility_threshold,
                    compatible=compatible,
                )
            )
            if compatible:
                neighbors[left_id].add(right_id)
                neighbors[right_id].add(left_id)

    cliques = _maximal_compatible_cliques(observation_ids, neighbors)
    all_ids = set(observation_ids)
    hypotheses = [
        _fuse_clique(
            clique,
            by_id=by_id,
            object_identity=object_identity,
            time_system=time_system,
            time_raw=time_raw,
            reference_frame=reference_frame,
            all_observation_ids=all_ids,
        )
        for clique in cliques
    ]

    set_document = {
        "object_identity": object_identity.model_dump(mode="json"),
        "time_system": time_system,
        "time_raw": time_raw,
        "reference_frame": reference_frame,
        "hypothesis_ids": [item.hypothesis_id for item in hypotheses],
        "pairwise_residuals": [item.model_dump(mode="json") for item in residuals],
    }
    suffix = canonical_digest(set_document).split(":", 1)[1][:16]

    return SdaHypothesisSet(
        set_id=f"SDA-HYPSET-{suffix}",
        object_identity=object_identity,
        time_system=time_system,
        time_raw=time_raw,
        reference_frame=reference_frame,
        hypotheses=hypotheses,
        pairwise_residuals=residuals,
        requires_resolution=len(hypotheses) > 1,
    )


def sda_hypothesis_evidence_graph(
    *,
    graph_id: str,
    observations: Iterable[SdaCanonicalEnvelope],
    hypothesis_set: SdaHypothesisSet,
) -> EvidenceGraph:
    ordered = sorted(list(observations), key=lambda item: item.observation_id)
    by_id = {item.observation_id: item for item in ordered}

    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []

    for observation in ordered:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"sda-canonical:{observation.observation_id}",
                node_type="sda_canonical_state_evidence",
                label=observation.observation_id,
                source_ref=f"source:{observation.source.source_id}",
                confidence=None,
                attributes={
                    "semantic_digest": observation.semantic_digest(),
                    "source_id": observation.source.source_id,
                    "source_standard": observation.source_standard,
                    "source_profile": observation.source_profile,
                },
            )
        )

    for hypothesis in hypothesis_set.hypotheses:
        hypothesis_node = f"sda-hypothesis:{hypothesis.hypothesis_id}"
        nodes.append(
            EvidenceGraphNode(
                node_id=hypothesis_node,
                node_type="sda_state_hypothesis",
                label=hypothesis.hypothesis_id,
                attributes=hypothesis.model_dump(mode="json"),
            )
        )
        for observation_id in hypothesis.support_observation_ids:
            if observation_id not in by_id:
                raise SdaHypothesisError(
                    "hypothesis references observation absent from graph input"
                )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"supports:{observation_id}:{hypothesis.hypothesis_id}",
                    source_node_id=f"sda-canonical:{observation_id}",
                    target_node_id=hypothesis_node,
                    relation="supports_hypothesis",
                    source_ref=f"observation:{observation_id}",
                    confidence=1.0,
                )
            )
        for observation_id in hypothesis.conflicting_observation_ids:
            if observation_id not in by_id:
                raise SdaHypothesisError(
                    "conflict references observation absent from graph input"
                )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"conflicts:{observation_id}:{hypothesis.hypothesis_id}",
                    source_node_id=f"sda-canonical:{observation_id}",
                    target_node_id=hypothesis_node,
                    relation="conflicts_with_hypothesis",
                    source_ref=f"observation:{observation_id}",
                    confidence=1.0,
                )
            )

    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)

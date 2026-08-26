from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any

from pydantic import BaseModel, Field

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


class Observation(BaseModel):
    observation_id: str = Field(min_length=1)
    sensor_id: str = Field(min_length=1)
    t_seconds: float
    x: float
    y: float
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class FusedTrack:
    track_id: str
    x: float
    y: float
    t_seconds: float
    confidence: float
    source_observation_ids: tuple[str, ...]
    source_sensor_ids: tuple[str, ...]


def _distance(a: Observation, b: Observation) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def associate_observations(
    observations: list[Observation],
    *,
    max_spatial_distance: float,
    max_time_delta_seconds: float,
) -> tuple[tuple[Observation, ...], ...]:
    """Greedy deterministic association for the frozen synthetic benchmark.

    This is not an operational tracker, JPDA/MHT implementation, or validated
    aerospace sensor-fusion algorithm.
    """
    ordered = sorted(observations, key=lambda item: (item.t_seconds, item.observation_id))
    groups: list[list[Observation]] = []
    for observation in ordered:
        placed = False
        for group in groups:
            anchor = group[0]
            if (
                abs(observation.t_seconds - anchor.t_seconds) <= max_time_delta_seconds
                and _distance(observation, anchor) <= max_spatial_distance
            ):
                group.append(observation)
                placed = True
                break
        if not placed:
            groups.append([observation])
    return tuple(tuple(group) for group in groups)


def fuse_group(group: tuple[Observation, ...], *, track_id: str) -> FusedTrack:
    total_weight = sum(max(obs.confidence, 1e-9) for obs in group)
    x = sum(obs.x * max(obs.confidence, 1e-9) for obs in group) / total_weight
    y = sum(obs.y * max(obs.confidence, 1e-9) for obs in group) / total_weight
    t_seconds = sum(obs.t_seconds * max(obs.confidence, 1e-9) for obs in group) / total_weight
    confidence = min(1.0, sum(obs.confidence for obs in group) / len(group))
    return FusedTrack(
        track_id=track_id,
        x=x,
        y=y,
        t_seconds=t_seconds,
        confidence=confidence,
        source_observation_ids=tuple(sorted(obs.observation_id for obs in group)),
        source_sensor_ids=tuple(sorted({obs.sensor_id for obs in group})),
    )


def fuse_observations(
    observations: list[Observation],
    *,
    max_spatial_distance: float,
    max_time_delta_seconds: float,
) -> tuple[FusedTrack, ...]:
    groups = associate_observations(
        observations,
        max_spatial_distance=max_spatial_distance,
        max_time_delta_seconds=max_time_delta_seconds,
    )
    tracks = [fuse_group(group, track_id=f"F{index:03d}") for index, group in enumerate(groups, start=1)]
    return tuple(sorted(tracks, key=lambda track: (track.x, track.y, track.track_id)))


def fusion_graph(
    *,
    graph_id: str,
    observations: list[Observation],
    tracks: tuple[FusedTrack, ...],
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    for observation in observations:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"obs:{observation.observation_id}",
                node_type="sensor_observation",
                label=observation.observation_id,
                source_ref=f"sensor:{observation.sensor_id}",
                confidence=observation.confidence,
                attributes=observation.model_dump(mode="json"),
            )
        )
    for track in tracks:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"track:{track.track_id}",
                node_type="synthetic_fused_track",
                label=track.track_id,
                confidence=track.confidence,
                attributes={
                    "x": track.x,
                    "y": track.y,
                    "t_seconds": track.t_seconds,
                    "source_observation_ids": list(track.source_observation_ids),
                    "source_sensor_ids": list(track.source_sensor_ids),
                },
            )
        )
        for observation_id in track.source_observation_ids:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"edge:{observation_id}:{track.track_id}",
                    source_node_id=f"obs:{observation_id}",
                    target_node_id=f"track:{track.track_id}",
                    relation="contributes_to",
                    source_ref=f"observation:{observation_id}",
                    confidence=1.0,
                )
            )
    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)

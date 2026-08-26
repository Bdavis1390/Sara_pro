from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from .prime import ActionProposal
from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


class MissionEvent(BaseModel):
    sequence: int = Field(ge=1)
    t_seconds: float = Field(ge=0)
    source: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class DebriefFinding:
    finding_type: str
    summary: str
    source_sequences: tuple[int, ...]
    confidence: float


def replay_events(events: list[MissionEvent]) -> tuple[MissionEvent, ...]:
    ordered = tuple(sorted(events, key=lambda event: (event.sequence, event.t_seconds)))
    seen: set[int] = set()
    for event in ordered:
        if event.sequence in seen:
            raise ValueError(f"duplicate mission-event sequence: {event.sequence}")
        seen.add(event.sequence)
    return ordered


def derive_findings(events: tuple[MissionEvent, ...]) -> tuple[DebriefFinding, ...]:
    findings: list[DebriefFinding] = []
    by_type: dict[str, list[MissionEvent]] = {}
    for event in events:
        by_type.setdefault(event.event_type, []).append(event)

    if by_type.get("comms_degraded"):
        seqs = tuple(event.sequence for event in by_type["comms_degraded"])
        findings.append(
            DebriefFinding(
                finding_type="communications_degradation",
                summary="Mission experienced a recorded communications-degradation event.",
                source_sequences=seqs,
                confidence=1.0,
            )
        )

    if by_type.get("sensor_stale"):
        seqs = tuple(event.sequence for event in by_type["sensor_stale"])
        findings.append(
            DebriefFinding(
                finding_type="stale_sensor_dependency",
                summary="Mission consumed or encountered stale sensor state requiring review.",
                source_sequences=seqs,
                confidence=1.0,
            )
        )

    if by_type.get("task_failed"):
        seqs = tuple(event.sequence for event in by_type["task_failed"])
        findings.append(
            DebriefFinding(
                finding_type="task_failure",
                summary="At least one mission task failed and requires causal review.",
                source_sequences=seqs,
                confidence=1.0,
            )
        )

    return tuple(sorted(findings, key=lambda finding: finding.finding_type))


def propose_follow_on_actions(
    findings: tuple[DebriefFinding, ...],
) -> tuple[ActionProposal, ...]:
    mapping = {
        "communications_degradation": "validate_alternate_comms_path",
        "stale_sensor_dependency": "tighten_stale_data_gate",
        "task_failure": "review_task_reassignment_policy",
    }
    proposals: list[ActionProposal] = []
    for index, finding in enumerate(findings, start=1):
        action = mapping.get(finding.finding_type)
        if action is None:
            continue
        proposals.append(
            ActionProposal(
                proposal_id=f"MISSION-COA-{index:03d}",
                action=action,
                rationale=[finding.summary],
                authority_required="identified-human-authority",
            )
        )
    return tuple(proposals)


def mission_replay_graph(
    *,
    graph_id: str,
    events: tuple[MissionEvent, ...],
    findings: tuple[DebriefFinding, ...],
    proposals: tuple[ActionProposal, ...],
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []

    for event in events:
        nodes.append(
            EvidenceGraphNode(
                node_id=f"event:{event.sequence}",
                node_type="mission_event",
                label=event.event_type,
                source_ref=f"event-sequence:{event.sequence}",
                confidence=1.0,
                attributes={
                    "t_seconds": event.t_seconds,
                    "source": event.source,
                    "payload": event.payload,
                },
            )
        )

    for index, finding in enumerate(findings, start=1):
        finding_id = f"finding:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=finding_id,
                node_type="debrief_finding",
                label=finding.finding_type,
                confidence=finding.confidence,
                attributes={"summary": finding.summary},
            )
        )
        for sequence in finding.source_sequences:
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"edge:event:{sequence}:finding:{index}",
                    source_node_id=f"event:{sequence}",
                    target_node_id=finding_id,
                    relation="supports",
                    source_ref=f"event-sequence:{sequence}",
                    confidence=finding.confidence,
                )
            )

    for index, proposal in enumerate(proposals, start=1):
        proposal_id = f"proposal:{index}"
        nodes.append(
            EvidenceGraphNode(
                node_id=proposal_id,
                node_type="prime_action_proposal",
                label=proposal.action,
                attributes=proposal.model_dump(mode="json"),
            )
        )
        if index <= len(findings):
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"edge:finding:{index}:proposal:{index}",
                    source_node_id=f"finding:{index}",
                    target_node_id=proposal_id,
                    relation="informs",
                )
            )

    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)

from __future__ import annotations

from collections.abc import Iterable

from .mission_replay import MissionEvent
from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode
from .sovereign_boundary_kernel import SovereignBoundaryEnvelope, boundary_event_payload, verify_boundary_envelope


class SovereignBoundaryReplayError(ValueError):
    pass


def boundary_transition_to_mission_event(
    envelope: SovereignBoundaryEnvelope,
    *,
    sequence: int,
    t_seconds: float,
) -> MissionEvent:
    if not verify_boundary_envelope(envelope):
        raise SovereignBoundaryReplayError("cannot replay an unverified SBK envelope")
    return MissionEvent(
        sequence=sequence,
        t_seconds=t_seconds,
        source="SOVEREIGN_BOUNDARY_KERNEL",
        event_type="sovereign_boundary_transition",
        payload=boundary_event_payload(envelope),
    )


def boundary_transition_events(
    envelopes: Iterable[SovereignBoundaryEnvelope],
    *,
    start_sequence: int = 1,
    step_seconds: float = 1.0,
) -> tuple[MissionEvent, ...]:
    if start_sequence < 1:
        raise SovereignBoundaryReplayError("start_sequence must be >= 1")
    if step_seconds < 0:
        raise SovereignBoundaryReplayError("step_seconds must be >= 0")
    events: list[MissionEvent] = []
    for offset, envelope in enumerate(envelopes):
        events.append(
            boundary_transition_to_mission_event(
                envelope,
                sequence=start_sequence + offset,
                t_seconds=offset * step_seconds,
            )
        )
    return tuple(events)


def sovereign_boundary_evidence_graph(
    *,
    graph_id: str,
    envelopes: Iterable[SovereignBoundaryEnvelope],
) -> EvidenceGraph:
    """Build a compact authority/provenance graph without copying raw action parameters."""

    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    seen: set[str] = set()

    for envelope in envelopes:
        if not verify_boundary_envelope(envelope):
            raise SovereignBoundaryReplayError("cannot graph an unverified SBK envelope")
        if envelope.envelope_id in seen:
            raise SovereignBoundaryReplayError(
                f"duplicate SBK envelope_id in graph input: {envelope.envelope_id}"
            )
        seen.add(envelope.envelope_id)
        prefix = f"sbk:{envelope.envelope_id}"
        action_node = f"{prefix}:action"
        policy_node = f"{prefix}:policy"
        envelope_node = f"{prefix}:envelope"

        nodes.append(
            EvidenceGraphNode(
                node_id=action_node,
                node_type="sbk_bound_action",
                label=envelope.action.action_type,
                source_ref=envelope.action_digest,
                confidence=1.0,
                attributes={
                    "domain": envelope.action.domain.value,
                    "resource": envelope.action.resource,
                    "effect_scope": envelope.action.effect_scope.value,
                    "capability_status": envelope.action.capability_status.value,
                    "action_digest": envelope.action_digest,
                    "raw_parameters_included": False,
                },
            )
        )
        nodes.append(
            EvidenceGraphNode(
                node_id=policy_node,
                node_type="sbk_policy_decision",
                label=envelope.policy.disposition.value,
                source_ref=envelope.policy.policy_revision,
                confidence=1.0,
                attributes={
                    "decided_by": envelope.policy.decided_by,
                    "policy_revision": envelope.policy.policy_revision,
                    "requirements": list(envelope.policy.requirements),
                    "human_approval_required": envelope.policy.human_approval_required,
                },
            )
        )
        nodes.append(
            EvidenceGraphNode(
                node_id=envelope_node,
                node_type="sbk_envelope",
                label=envelope.state.value,
                source_ref=envelope.envelope_digest,
                confidence=1.0,
                attributes={
                    "actor": envelope.actor,
                    "environment": envelope.context.environment.value,
                    "mission_id": envelope.context.mission_id,
                    "network_state": envelope.context.network_state,
                    "envelope_digest": envelope.envelope_digest,
                },
            )
        )
        edges.extend(
            [
                EvidenceGraphEdge(
                    edge_id=f"{prefix}:edge:policy-governs-action",
                    source_node_id=policy_node,
                    target_node_id=action_node,
                    relation="governs",
                    confidence=1.0,
                ),
                EvidenceGraphEdge(
                    edge_id=f"{prefix}:edge:action-bound-to-envelope",
                    source_node_id=action_node,
                    target_node_id=envelope_node,
                    relation="bound_by_digest",
                    source_ref=envelope.action_digest,
                    confidence=1.0,
                ),
            ]
        )

        if envelope.human_approval_ref:
            approval_node = f"{prefix}:human-approval"
            nodes.append(
                EvidenceGraphNode(
                    node_id=approval_node,
                    node_type="human_approval",
                    label="human approval",
                    source_ref=envelope.human_approval_ref,
                    confidence=1.0,
                    attributes={"approver": envelope.human_approver},
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"{prefix}:edge:approval-authorizes-envelope",
                    source_node_id=approval_node,
                    target_node_id=envelope_node,
                    relation="authorizes",
                    source_ref=envelope.human_approval_ref,
                    confidence=1.0,
                )
            )

        if envelope.prime_authorization_ref:
            prime_node = f"{prefix}:prime-authorization"
            nodes.append(
                EvidenceGraphNode(
                    node_id=prime_node,
                    node_type="prime_sentinel_authorization",
                    label="PRIME SENTINEL effect authorization",
                    source_ref=envelope.prime_authorization_ref,
                    confidence=1.0,
                    attributes={
                        "key_fingerprint_sha256": envelope.prime_authorization_key_fingerprint_sha256,
                    },
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"{prefix}:edge:prime-authorizes-envelope",
                    source_node_id=prime_node,
                    target_node_id=envelope_node,
                    relation="purpose_bound_authorization",
                    source_ref=envelope.prime_authorization_ref,
                    confidence=1.0,
                )
            )

        if envelope.execution_result is not None:
            result_node = f"{prefix}:execution-result"
            nodes.append(
                EvidenceGraphNode(
                    node_id=result_node,
                    node_type="sbk_execution_result",
                    label=envelope.execution_result.status.value,
                    source_ref=envelope.execution_result.outcome_ref,
                    confidence=1.0,
                    attributes={
                        "outcome_ref": envelope.execution_result.outcome_ref,
                        "evidence_refs": list(envelope.execution_result.evidence_refs),
                    },
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    edge_id=f"{prefix}:edge:envelope-produces-result",
                    source_node_id=envelope_node,
                    target_node_id=result_node,
                    relation="produces",
                    confidence=1.0,
                )
            )

    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)

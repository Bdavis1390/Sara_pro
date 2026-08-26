from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .qualification import EvidenceGraph, EvidenceGraphEdge, EvidenceGraphNode


@dataclass(frozen=True)
class ApntDecision:
    operational_state: str
    confidence: float
    recovery_options: tuple[str, ...]
    rationale: tuple[str, ...]


def derive_apnt_decision(source_state: dict[str, dict[str, Any]]) -> ApntDecision:
    """Derive a bounded synthetic APNT-awareness state from normalized source health.

    This is a demonstrator rule set, not a navigation solution or sensor-fusion algorithm.
    It intentionally produces operator-awareness/recovery metadata only.
    """
    gnss = source_state.get("gnss_primary", {})
    ins = source_state.get("ins_primary", {})
    alt = source_state.get("alt_pnt_1", {})

    gnss_conf = float(gnss.get("confidence", 0.0))
    ins_conf = float(ins.get("confidence", 0.0))
    alt_conf = float(alt.get("confidence", 0.0))
    gnss_health = str(gnss.get("health", "UNKNOWN"))

    rationale: list[str] = []
    recovery: list[str] = []

    if gnss_health in {"UNTRUSTED", "DENIED"} or gnss_conf < 0.25:
        state = "GNSS_DENIED"
        rationale.append("primary GNSS confidence is below trusted-use threshold")
        recovery.extend(["exclude_gnss", "fuse_ins_alt_pnt", "request_operator_approval"])
        confidence = max(ins_conf, alt_conf)
    elif gnss_health == "RECOVERING":
        state = "RECOVERY"
        rationale.append("primary GNSS is recovering and requires cross-validation")
        recovery.extend(["cross_validate_gnss_before_reentry", "retain_alt_pnt", "operator_review"])
        confidence = max(ins_conf, alt_conf)
    elif gnss_health == "DEGRADED" or gnss_conf < 0.70:
        state = "DEGRADED_PNT"
        rationale.append("primary GNSS is degraded or below nominal confidence")
        recovery.extend(["weight_ins_more", "enable_alt_pnt_cross_check", "alert_operator"])
        confidence = max(gnss_conf, ins_conf, alt_conf)
    else:
        state = "NORMAL"
        rationale.append("normalized source set is within nominal demonstrator thresholds")
        confidence = max(gnss_conf, ins_conf, alt_conf)

    return ApntDecision(
        operational_state=state,
        confidence=round(confidence, 4),
        recovery_options=tuple(recovery),
        rationale=tuple(rationale),
    )


def apnt_snapshot_graph(
    *,
    graph_id: str,
    source_state: dict[str, dict[str, Any]],
    decision: ApntDecision,
) -> EvidenceGraph:
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []

    for source_id, state in sorted(source_state.items()):
        nodes.append(
            EvidenceGraphNode(
                node_id=f"source:{source_id}",
                node_type="apnt_source_state",
                label=source_id,
                confidence=float(state.get("confidence", 0.0)),
                attributes=dict(state),
            )
        )

    nodes.extend(
        [
            EvidenceGraphNode(
                node_id="derived:operational_state",
                node_type="derived_state",
                label=decision.operational_state,
                confidence=decision.confidence,
                attributes={"rationale": list(decision.rationale)},
            ),
            EvidenceGraphNode(
                node_id="policy:recovery_options",
                node_type="policy_candidate_set",
                label="recovery options",
                attributes={"options": list(decision.recovery_options)},
            ),
        ]
    )

    for source_id in sorted(source_state):
        edges.append(
            EvidenceGraphEdge(
                edge_id=f"edge:{source_id}:state",
                source_node_id=f"source:{source_id}",
                target_node_id="derived:operational_state",
                relation="contributes_to",
            )
        )

    edges.append(
        EvidenceGraphEdge(
            edge_id="edge:state:recovery",
            source_node_id="derived:operational_state",
            target_node_id="policy:recovery_options",
            relation="informs",
        )
    )
    return EvidenceGraph(graph_id=graph_id, nodes=nodes, edges=edges)

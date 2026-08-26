from __future__ import annotations

from typing import Any

from .qualification import EvidenceGraph, canonical_digest


def evidence_graph_to_neutral_model(graph: EvidenceGraph) -> dict[str, Any]:
    """Project an Evidence Graph into a canonical Worldshepherd neutral model.

    This is an intermediate representation only. It is not SysML, XMI, Cameo,
    MagicDraw, or any other vendor/government modeling standard.
    """
    model = {
        "schema": "WS-NEUTRAL-SYSTEM-MODEL-V1",
        "source_graph_id": graph.graph_id,
        "elements": [
            {
                "id": node.node_id,
                "type": node.node_type,
                "name": node.label,
                "source_ref": node.source_ref,
                "confidence": node.confidence,
                "attributes": node.attributes,
            }
            for node in sorted(graph.nodes, key=lambda item: item.node_id)
        ],
        "relationships": [
            {
                "id": edge.edge_id,
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "type": edge.relation,
                "source_ref": edge.source_ref,
                "confidence": edge.confidence,
                "attributes": edge.attributes,
            }
            for edge in sorted(graph.edges, key=lambda item: item.edge_id)
        ],
        "claims_boundary": [
            "Neutral internal representation only.",
            "No SysML/XMI/Cameo/MagicDraw compatibility is inferred from this projection.",
        ],
    }
    model["model_digest"] = canonical_digest(model)
    return model


def export_sysml_xmi_stub(model: dict[str, Any]) -> str:
    raise NotImplementedError(
        "SysML/XMI export is not implemented or validated; authoritative target schema/tool interoperability must be established first"
    )

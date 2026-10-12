from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

class NodeKind(str, Enum):
    EVIDENCE = "EVIDENCE"
    INTERPRETATION = "INTERPRETATION"
    ASSUMPTION = "ASSUMPTION"
    MODEL = "MODEL"
    CLAIM = "CLAIM"
    DECISION_SUPPORT = "DECISION_SUPPORT"

class Validity(str, Enum):
    CURRENT = "CURRENT"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"

@dataclass
class EvidenceNode:
    node_id: str
    kind: NodeKind
    fingerprint: str
    validity: Validity = Validity.CURRENT
    domain: str | None = None
    materiality_note: str | None = None

@dataclass(frozen=True)
class DependencyEdge:
    parent: str
    child: str
    material: bool = True
    rationale: str | None = None

class EvidenceBOM:
    def __init__(self) -> None:
        self.nodes: dict[str, EvidenceNode] = {}
        self.parents: dict[str, list[DependencyEdge]] = {}
        self.children: dict[str, list[DependencyEdge]] = {}

    def add_node(self, node: EvidenceNode) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"duplicate node: {node.node_id}")
        self.nodes[node.node_id] = node

    def add_dependency(self, edge: DependencyEdge) -> None:
        if edge.parent not in self.nodes or edge.child not in self.nodes:
            raise ValueError("dependency endpoints must exist")
        self.parents.setdefault(edge.child, []).append(edge)
        self.children.setdefault(edge.parent, []).append(edge)
        if self._has_cycle():
            self.parents[edge.child].pop()
            self.children[edge.parent].pop()
            raise ValueError("EBOM must remain acyclic")

    def _has_cycle(self) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> bool:
            if node_id in visiting:
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            for edge in self.children.get(node_id, []):
                if visit(edge.child):
                    return True
            visiting.remove(node_id)
            visited.add(node_id)
            return False

        return any(visit(n) for n in self.nodes)

    def update_fingerprint(self, node_id: str, new_fingerprint: str) -> list[str]:
        node = self.nodes[node_id]
        if node.fingerprint == new_fingerprint:
            return []
        node.fingerprint = new_fingerprint
        node.validity = Validity.CURRENT
        return self.invalidate_descendants(node_id)

    def invalidate_descendants(self, node_id: str) -> list[str]:
        invalidated: list[str] = []
        stack = [node_id]
        seen = {node_id}
        while stack:
            current = stack.pop()
            for edge in self.children.get(current, []):
                if not edge.material:
                    continue
                child = edge.child
                if child in seen:
                    continue
                seen.add(child)
                self.nodes[child].validity = Validity.REVALIDATION_REQUIRED
                invalidated.append(child)
                stack.append(child)
        return invalidated

    def blast_radius(self, node_id: str) -> dict:
        descendants = []
        stack = [node_id]
        seen = {node_id}
        while stack:
            current = stack.pop()
            for edge in self.children.get(current, []):
                if not edge.material or edge.child in seen:
                    continue
                seen.add(edge.child)
                descendants.append(edge.child)
                stack.append(edge.child)
        by_domain: dict[str, int] = {}
        for item in descendants:
            domain = self.nodes[item].domain or "unspecified"
            by_domain[domain] = by_domain.get(domain, 0) + 1
        return {
            "source_node": node_id,
            "material_descendants": descendants,
            "count": len(descendants),
            "by_domain": by_domain,
        }

    def promotable(self, node_id: str) -> bool:
        node = self.nodes[node_id]
        if node.validity != Validity.CURRENT:
            return False
        for edge in self.parents.get(node_id, []):
            if edge.material and self.nodes[edge.parent].validity != Validity.CURRENT:
                return False
        return True

"""Dependency-aware evidence and claim invalidation for BAROS research.

NON-CLINICAL. This module tracks which bounded BAROS claims depend on which
artifacts/assumptions so that changed, contradicted, or revoked evidence can
propagate a downgrade instead of leaving stale claims active.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


ALLOWED_NODE_KINDS = {
    "raw_evidence",
    "analysis",
    "assumption",
    "model",
    "configuration",
    "claim",
    "authorization",
}


@dataclass(frozen=True)
class EvidenceNode:
    node_id: str
    kind: str
    valid: bool = True
    quarantined: bool = False
    reason: str | None = None

    def validate(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must be non-empty")
        if self.kind not in ALLOWED_NODE_KINDS:
            raise ValueError(f"unsupported evidence node kind: {self.kind}")
        if self.quarantined and self.valid:
            raise ValueError("quarantined evidence cannot simultaneously be valid")


@dataclass(frozen=True)
class ClaimAssessment:
    claim_id: str
    eligible: bool
    invalid_dependencies: tuple[str, ...]
    quarantined_dependencies: tuple[str, ...]
    unresolved_dependencies: tuple[str, ...]


class EvidenceDependencyGraph:
    """Directed acyclic dependency graph with blast-radius invalidation."""

    def __init__(self, nodes: Sequence[EvidenceNode], dependencies: Mapping[str, Sequence[str]]):
        self.nodes = {node.node_id: node for node in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("duplicate evidence node_id")
        for node in nodes:
            node.validate()

        self.dependencies: dict[str, tuple[str, ...]] = {}
        for node_id, deps in dependencies.items():
            if node_id not in self.nodes:
                raise ValueError(f"dependency target does not exist: {node_id}")
            rendered = tuple(str(dep) for dep in deps)
            missing = [dep for dep in rendered if dep not in self.nodes]
            if missing:
                raise ValueError(f"unknown dependencies for {node_id}: {', '.join(missing)}")
            if node_id in rendered:
                raise ValueError("self-dependency is not allowed")
            self.dependencies[node_id] = rendered

        for node_id in self.nodes:
            self.dependencies.setdefault(node_id, ())
        self._assert_acyclic()

    def _assert_acyclic(self) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            if node_id in visiting:
                raise ValueError("evidence dependency graph contains a cycle")
            visiting.add(node_id)
            for dep in self.dependencies[node_id]:
                visit(dep)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in self.nodes:
            visit(node_id)

    def transitive_dependencies(self, node_id: str) -> tuple[str, ...]:
        if node_id not in self.nodes:
            raise ValueError(f"unknown node: {node_id}")
        result: set[str] = set()

        def collect(current: str) -> None:
            for dep in self.dependencies[current]:
                if dep not in result:
                    result.add(dep)
                    collect(dep)

        collect(node_id)
        return tuple(sorted(result))

    def assess_claim(self, claim_id: str) -> ClaimAssessment:
        node = self.nodes.get(claim_id)
        if node is None or node.kind != "claim":
            raise ValueError("claim_id must identify a claim node")
        deps = self.transitive_dependencies(claim_id)
        invalid = tuple(sorted(dep for dep in deps if not self.nodes[dep].valid))
        quarantined = tuple(sorted(dep for dep in deps if self.nodes[dep].quarantined))
        unresolved = tuple(
            sorted(
                dep
                for dep in deps
                if self.nodes[dep].reason
                and not self.nodes[dep].valid
                and not self.nodes[dep].quarantined
            )
        )
        eligible = node.valid and not node.quarantined and not invalid and not quarantined
        return ClaimAssessment(
            claim_id=claim_id,
            eligible=eligible,
            invalid_dependencies=invalid,
            quarantined_dependencies=quarantined,
            unresolved_dependencies=unresolved,
        )

    def blast_radius(self, changed_node_ids: Iterable[str]) -> tuple[str, ...]:
        """Return claims transitively dependent on changed/quarantined evidence."""
        changed = {str(item) for item in changed_node_ids}
        unknown = changed - self.nodes.keys()
        if unknown:
            raise ValueError("unknown changed nodes: " + ", ".join(sorted(unknown)))
        affected: list[str] = []
        for node_id, node in self.nodes.items():
            if node.kind != "claim":
                continue
            deps = set(self.transitive_dependencies(node_id))
            if deps & changed:
                affected.append(node_id)
        return tuple(sorted(affected))

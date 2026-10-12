from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256

class LayerKind(str, Enum):
    WITNESS = "WITNESS"
    DIPLOMATIC = "DIPLOMATIC"
    NORMALIZED = "NORMALIZED"
    TRANSLITERATION = "TRANSLITERATION"
    LEMMA_ANALYSIS = "LEMMA_ANALYSIS"
    MORPHOSYNTAX = "MORPHOSYNTAX"
    TRANSLATION = "TRANSLATION"
    INTERPRETATION = "INTERPRETATION"
    METADATA_SUMMARY = "METADATA_SUMMARY"

class LayerState(str, Enum):
    CURRENT = "CURRENT"
    STALE_PENDING_REAUDIT = "STALE_PENDING_REAUDIT"
    SUPERSEDED = "SUPERSEDED"
    UNRESOLVED = "UNRESOLVED"

@dataclass
class TranslationLayer:
    layer_id: str
    kind: LayerKind
    content: str
    version_ref: str | None = None
    source_refs: list[str] = field(default_factory=list)
    uncertainty: list[str] = field(default_factory=list)
    state: LayerState = LayerState.CURRENT

    @property
    def fingerprint(self) -> str:
        payload = "\n".join([
            self.kind.value,
            self.version_ref or "",
            self.content,
            *sorted(self.source_refs),
            *sorted(self.uncertainty),
        ])
        return sha256(payload.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class TranslationDependency:
    upstream: str
    downstream: str
    material: bool = True
    pinned_upstream_fingerprint: str | None = None
    rationale: str | None = None

class TranslationLineageGraph:
    def __init__(self) -> None:
        self.layers: dict[str, TranslationLayer] = {}
        self.children: dict[str, list[TranslationDependency]] = {}
        self.parents: dict[str, list[TranslationDependency]] = {}

    def add_layer(self, layer: TranslationLayer) -> None:
        if layer.layer_id in self.layers:
            raise ValueError(f"duplicate layer {layer.layer_id}")
        self.layers[layer.layer_id] = layer

    def add_dependency(self, dep: TranslationDependency) -> None:
        if dep.upstream not in self.layers or dep.downstream not in self.layers:
            raise ValueError("dependency endpoints must exist")
        self.children.setdefault(dep.upstream, []).append(dep)
        self.parents.setdefault(dep.downstream, []).append(dep)
        if self._has_cycle():
            self.children[dep.upstream].pop()
            self.parents[dep.downstream].pop()
            raise ValueError("translation lineage must remain acyclic")

    def _has_cycle(self) -> bool:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for dep in self.children.get(node, []):
                if visit(dep.downstream):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in self.layers)

    def unpinned_material_dependencies(self, layer_id: str) -> list[str]:
        return [
            dep.upstream
            for dep in self.parents.get(layer_id, [])
            if dep.material and dep.pinned_upstream_fingerprint is None
        ]

    def stale_dependencies(self, layer_id: str) -> list[str]:
        stale: list[str] = []
        for dep in self.parents.get(layer_id, []):
            if not dep.material:
                continue
            upstream = self.layers[dep.upstream]
            if dep.pinned_upstream_fingerprint is None:
                stale.append(dep.upstream)
            elif dep.pinned_upstream_fingerprint != upstream.fingerprint:
                stale.append(dep.upstream)
            elif upstream.state != LayerState.CURRENT:
                stale.append(dep.upstream)
        return stale

    def invalidate_from(self, upstream_id: str) -> list[str]:
        invalidated: list[str] = []
        stack = [upstream_id]
        seen = {upstream_id}
        while stack:
            current = stack.pop()
            for dep in self.children.get(current, []):
                if not dep.material or dep.downstream in seen:
                    continue
                seen.add(dep.downstream)
                self.layers[dep.downstream].state = LayerState.STALE_PENDING_REAUDIT
                invalidated.append(dep.downstream)
                stack.append(dep.downstream)
        return invalidated

    def translation_claim_ceiling(self, translation_id: str) -> str:
        layer = self.layers[translation_id]
        if layer.kind != LayerKind.TRANSLATION:
            raise ValueError("claim ceiling requested for non-translation layer")
        if layer.state == LayerState.SUPERSEDED:
            return "DO_NOT_USE_AS_CURRENT_WITHOUT_REVISION"
        if layer.state == LayerState.STALE_PENDING_REAUDIT:
            return "STALE_PENDING_REAUDIT"
        if self.stale_dependencies(translation_id):
            return "STALE_PENDING_REAUDIT"
        if layer.uncertainty:
            return "TRANSLATION_WITH_MATERIAL_UNCERTAINTY"
        return "CURRENTLY_STABLE_WITHIN_AUDITED_EVIDENCE"

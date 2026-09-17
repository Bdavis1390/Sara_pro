from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256

@dataclass(frozen=True)
class LayerVersion:
    layer_id: str
    content: str
    version_ref: str | None = None
    depends_on_hash: str | None = None

    @property
    def content_hash(self) -> str:
        return sha256(self.content.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class DependencyStatus:
    stale: bool
    reason: str
    current_upstream_hash: str
    recorded_dependency_hash: str | None

def check_dependency(upstream: LayerVersion, downstream: LayerVersion) -> DependencyStatus:
    current = upstream.content_hash
    recorded = downstream.depends_on_hash
    if recorded is None:
        return DependencyStatus(
            stale=True,
            reason="DOWNSTREAM_DEPENDENCY_UNPINNED",
            current_upstream_hash=current,
            recorded_dependency_hash=None,
        )
    if recorded != current:
        return DependencyStatus(
            stale=True,
            reason="UPSTREAM_CONTENT_CHANGED",
            current_upstream_hash=current,
            recorded_dependency_hash=recorded,
        )
    return DependencyStatus(
        stale=False,
        reason="DEPENDENCY_CURRENT",
        current_upstream_hash=current,
        recorded_dependency_hash=recorded,
    )

def named_entity_mismatch(
    current_source_entities: set[str],
    downstream_entities: set[str],
) -> dict:
    missing = sorted(current_source_entities - downstream_entities)
    legacy_or_extra = sorted(downstream_entities - current_source_entities)
    return {
        "material_mismatch": bool(missing or legacy_or_extra),
        "missing_current_entities": missing,
        "legacy_or_extra_entities": legacy_or_extra,
    }

def publication_state(
    dependency: DependencyStatus,
    entity_check: dict,
) -> str:
    if dependency.stale or entity_check["material_mismatch"]:
        return "STALE_PENDING_REAUDIT"
    return "CURRENT_WITHIN_CHECKED_DEPENDENCIES"

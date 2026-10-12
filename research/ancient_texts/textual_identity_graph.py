from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class TextObjectKind(str, Enum):
    PHYSICAL_WITNESS = "PHYSICAL_WITNESS"
    RECENSION = "RECENSION"
    DAUGHTER_VERSION = "DAUGHTER_VERSION"
    RECONSTRUCTED_ARCHETYPE = "RECONSTRUCTED_ARCHETYPE"
    SCHOLARLY_COMPOSITE = "SCHOLARLY_COMPOSITE"
    CANONICAL_COLLECTION = "CANONICAL_COLLECTION"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class TextObject:
    object_id: str
    work_family: str
    kind: TextObjectKind
    language: str | None = None
    date_range: str | None = None
    physical: bool = False
    source_witnesses: tuple[str, ...] = ()
    note: str | None = None

@dataclass(frozen=True)
class TextRelation:
    parent: str
    child: str
    relation: str
    evidence_refs: tuple[str, ...] = ()
    confidence: float | None = None

class TextualIdentityGraph:
    def __init__(self) -> None:
        self.objects: dict[str, TextObject] = {}
        self.relations: list[TextRelation] = []

    def add_object(self, obj: TextObject) -> None:
        if obj.object_id in self.objects:
            raise ValueError(f"duplicate object {obj.object_id}")
        self.objects[obj.object_id] = obj

    def add_relation(self, rel: TextRelation) -> None:
        if rel.parent not in self.objects or rel.child not in self.objects:
            raise ValueError("relation endpoints must exist")
        if rel.confidence is not None and not (0.0 <= rel.confidence <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        self.relations.append(rel)

    def same_translation_target(self, a: str, b: str) -> bool:
        left = self.objects[a]
        right = self.objects[b]
        if left.object_id == right.object_id:
            return True
        if left.kind != right.kind:
            return False
        return (
            left.work_family == right.work_family
            and left.language == right.language
            and left.source_witnesses == right.source_witnesses
            and left.physical == right.physical
        )

    def requires_identity_label(self, object_id: str) -> bool:
        obj = self.objects[object_id]
        return (
            not obj.physical
            or obj.kind in {
                TextObjectKind.RECONSTRUCTED_ARCHETYPE,
                TextObjectKind.SCHOLARLY_COMPOSITE,
                TextObjectKind.CANONICAL_COLLECTION,
            }
            or len(obj.source_witnesses) > 1
        )

    def translation_target_claim(self, object_id: str) -> str:
        obj = self.objects[object_id]
        if obj.kind == TextObjectKind.UNKNOWN:
            return "TRANSLATION_TARGET_UNRESOLVED"
        if self.requires_identity_label(object_id):
            return "TRANSLATION_TARGET_MUST_BE_EXPLICITLY_LABELED"
        return "PHYSICAL_WITNESS_TARGET_EXPLICIT"

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256

class PSECStage(str, Enum):
    ARTIFACT = "ARTIFACT"
    TOMOGRAPHY = "TOMOGRAPHY"
    SURFACE_SEGMENTATION = "SURFACE_SEGMENTATION"
    VIRTUAL_UNWRAP = "VIRTUAL_UNWRAP"
    INK_DETECTION = "INK_DETECTION"
    GLYPH_IMAGE = "GLYPH_IMAGE"
    TRANSCRIPTION = "TRANSCRIPTION"
    TEXTUAL_RECONSTRUCTION = "TEXTUAL_RECONSTRUCTION"
    TRANSLATION = "TRANSLATION"
    INTERPRETATION = "INTERPRETATION"

@dataclass(frozen=True)
class StageArtifact:
    artifact_id: str
    stage: PSECStage
    content_ref: str
    version: str | None = None
    model_ref: str | None = None
    reviewer_ref: str | None = None
    uncertainty: float | None = None
    spatial_ref: str | None = None
    parent_fingerprints: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        payload = "\n".join([
            self.artifact_id,
            self.stage.value,
            self.content_ref,
            self.version or "",
            self.model_ref or "",
            self.reviewer_ref or "",
            "" if self.uncertainty is None else f"{self.uncertainty:.12g}",
            self.spatial_ref or "",
            *sorted(self.parent_fingerprints),
        ])
        return sha256(payload.encode("utf-8")).hexdigest()

@dataclass
class PhysicalSemanticChain:
    nodes: dict[str, StageArtifact] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)

    def add(self, node: StageArtifact) -> None:
        if node.artifact_id in self.nodes:
            raise ValueError(f"duplicate artifact {node.artifact_id}")
        self.nodes[node.artifact_id] = node

    def link(self, parent_id: str, child_id: str) -> None:
        if parent_id not in self.nodes or child_id not in self.nodes:
            raise ValueError("link endpoints must exist")
        self.children.setdefault(parent_id, []).append(child_id)

    def descendants(self, artifact_id: str) -> list[str]:
        out: list[str] = []
        stack = [artifact_id]
        seen = {artifact_id}
        while stack:
            current = stack.pop()
            for child in self.children.get(current, []):
                if child in seen:
                    continue
                seen.add(child)
                out.append(child)
                stack.append(child)
        return out

    def invalidate_from(self, artifact_id: str) -> list[str]:
        return self.descendants(artifact_id)

    def deepest_material_stage(self, artifact_id: str) -> PSECStage:
        node = self.nodes[artifact_id]
        return node.stage

def translation_requires_material_trace(
    translation: StageArtifact,
) -> str:
    if translation.stage != PSECStage.TRANSLATION:
        raise ValueError("expected translation stage")
    if not translation.parent_fingerprints:
        return "BLOCK_UNTRACED_TRANSLATION"
    return "TRANSLATION_TRACE_PRESENT"

def propagate_uncertainty(stage_uncertainties: list[float]) -> float:
    if not stage_uncertainties:
        return 0.0
    if any(not 0 <= x <= 1 for x in stage_uncertainties):
        raise ValueError("uncertainties must be in [0,1]")
    # Conservative independent-risk approximation.
    confidence = 1.0
    for uncertainty in stage_uncertainties:
        confidence *= (1.0 - uncertainty)
    return 1.0 - confidence

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from math import log
from typing import Mapping

class EvidenceChannel(str, Enum):
    TEXTUAL = "TEXTUAL"
    GEOMETRY = "GEOMETRY"
    DNA = "DNA"
    PROTEOMICS = "PROTEOMICS"
    INK_CHEMISTRY = "INK_CHEMISTRY"
    SPECTROSCOPY = "SPECTROSCOPY"
    MICROBIOME = "MICROBIOME"
    TOMOGRAPHY = "TOMOGRAPHY"
    PALEOGRAPHY = "PALEOGRAPHY"

class ChannelResult(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"
    UNRESOLVED = "UNRESOLVED"

@dataclass(frozen=True)
class MaterialEvidence:
    evidence_id: str
    channel: EvidenceChannel
    result: ChannelResult
    reliability: float
    source_ref: str
    independent_group: str
    note: str | None = None

    def validate(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be in [0,1]")
        if not self.source_ref:
            raise ValueError("source_ref required")
        if not self.independent_group:
            raise ValueError("independent_group required")

@dataclass
class ArtifactHypothesis:
    hypothesis_id: str
    statement: str
    evidence: list[MaterialEvidence] = field(default_factory=list)

    def add(self, item: MaterialEvidence) -> None:
        item.validate()
        self.evidence.append(item)

    def independent_channel_count(self) -> int:
        return len({e.independent_group for e in self.evidence})

    def conflicts(self) -> list[MaterialEvidence]:
        return [e for e in self.evidence if e.result == ChannelResult.CONTRADICTS]

    def supports(self) -> list[MaterialEvidence]:
        return [e for e in self.evidence if e.result == ChannelResult.SUPPORTS]

    def convergence_state(self) -> str:
        if self.conflicts():
            return "CONFLICT_REQUIRES_RECONCILIATION"
        support_groups = {
            e.independent_group
            for e in self.supports()
            if e.reliability >= 0.5
        }
        if len(support_groups) >= 3:
            return "MULTICHANNEL_CONVERGENCE"
        if len(support_groups) >= 2:
            return "ORTHOGONAL_SUPPORT"
        if len(support_groups) == 1:
            return "SINGLE_CHANNEL_SUPPORT"
        return "INSUFFICIENT_SUPPORT"

    def claim_ceiling(self) -> str:
        state = self.convergence_state()
        if state == "CONFLICT_REQUIRES_RECONCILIATION":
            return "HYPOTHESIS_UNDER_MATERIAL_CONFLICT"
        if state == "MULTICHANNEL_CONVERGENCE":
            return "STRONG_MULTICHANNEL_SUPPORT"
        if state == "ORTHOGONAL_SUPPORT":
            return "SUPPORTED_BY_INDEPENDENT_CHANNELS"
        if state == "SINGLE_CHANNEL_SUPPORT":
            return "SINGLE_CHANNEL_HYPOTHESIS"
        return "INSUFFICIENT_EVIDENCE"

def same_manuscript_join_gate(
    textual_similarity: bool,
    geometry_fit: bool,
    dna_compatible: bool | None,
) -> str:
    if dna_compatible is False:
        return "REJECT_JOIN_MATERIAL_CONTRADICTION"
    if textual_similarity and geometry_fit and dna_compatible is True:
        return "JOIN_STRONGLY_SUPPORTED"
    if textual_similarity and geometry_fit:
        return "JOIN_SUPPORTED_PENDING_ORTHOGONAL_EVIDENCE"
    return "JOIN_UNRESOLVED"

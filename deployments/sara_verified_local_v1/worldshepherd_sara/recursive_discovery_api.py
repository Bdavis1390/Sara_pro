from __future__ import annotations

from pydantic import BaseModel, Field

from .recursive_discovery import (
    DiscoveryEvidenceState,
    DiscoveryKind,
    ExpansionProposal,
    RecursiveDiscoveryPolicy,
)


class OmegaSeedSpec(BaseModel):
    kind: DiscoveryKind
    domain: str = Field(min_length=1, max_length=256)
    statement: str = Field(min_length=1, max_length=4096)
    source_refs: list[str] = Field(default_factory=list, max_length=32)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_state: DiscoveryEvidenceState = DiscoveryEvidenceState.UNVERIFIED
    cross_domain_tags: list[str] = Field(default_factory=list, max_length=32)
    falsification_tests: list[str] = Field(default_factory=list, max_length=32)


class OmegaInitializeRequest(BaseModel):
    seeds: list[OmegaSeedSpec] = Field(min_length=1, max_length=128)
    max_active_frontier: int = Field(default=4096, ge=1, le=4096)


class OmegaCycleRequest(BaseModel):
    proposals: list[ExpansionProposal] = Field(default_factory=list, max_length=128)
    policy: RecursiveDiscoveryPolicy = Field(default_factory=RecursiveDiscoveryPolicy)

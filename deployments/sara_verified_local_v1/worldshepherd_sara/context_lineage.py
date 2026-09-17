from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ContextSourceType(str, Enum):
    HUMAN_ROOT_INSTRUCTION = "HUMAN_ROOT_INSTRUCTION"
    SIGNED_POLICY = "SIGNED_POLICY"
    PRIME_SIGNED_AUTHORIZATION = "PRIME_SIGNED_AUTHORIZATION"
    TOOL_RESULT = "TOOL_RESULT"
    SOURCE_DOCUMENT = "SOURCE_DOCUMENT"
    MODEL_SUMMARY = "MODEL_SUMMARY"
    MODEL_MEMORY = "MODEL_MEMORY"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class TrustClass(str, Enum):
    ROOT = "ROOT"
    POLICY = "POLICY"
    EVIDENCE = "EVIDENCE"
    UNTRUSTED_DERIVED = "UNTRUSTED_DERIVED"


TRUST_BY_SOURCE: dict[ContextSourceType, TrustClass] = {
    ContextSourceType.HUMAN_ROOT_INSTRUCTION: TrustClass.ROOT,
    ContextSourceType.SIGNED_POLICY: TrustClass.POLICY,
    ContextSourceType.PRIME_SIGNED_AUTHORIZATION: TrustClass.POLICY,
    ContextSourceType.TOOL_RESULT: TrustClass.EVIDENCE,
    ContextSourceType.SOURCE_DOCUMENT: TrustClass.EVIDENCE,
    ContextSourceType.MODEL_SUMMARY: TrustClass.UNTRUSTED_DERIVED,
    ContextSourceType.MODEL_MEMORY: TrustClass.UNTRUSTED_DERIVED,
    ContextSourceType.MODEL_INFERENCE: TrustClass.UNTRUSTED_DERIVED,
}

AUTHORITY_GRANTING_SOURCES = {
    ContextSourceType.HUMAN_ROOT_INSTRUCTION,
    ContextSourceType.SIGNED_POLICY,
    ContextSourceType.PRIME_SIGNED_AUTHORIZATION,
}


class ContextArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1, max_length=128)
    source_type: ContextSourceType
    source_ref: str = Field(min_length=1, max_length=2048)
    content_hash: str = Field(min_length=1, max_length=256)
    parent_artifact_ids: list[str] = Field(default_factory=list)

    @property
    def trust_class(self) -> TrustClass:
        return TRUST_BY_SOURCE[self.source_type]

    @property
    def can_grant_authority(self) -> bool:
        return self.source_type in AUTHORITY_GRANTING_SOURCES


def evaluate_authority_claim(artifact: ContextArtifact) -> tuple[bool, list[str]]:
    if artifact.can_grant_authority:
        return True, [f"authority source accepted: {artifact.source_type.value}"]
    return False, [
        f"{artifact.source_type.value} is {artifact.trust_class.value} and cannot grant authority"
    ]


def evaluate_evidence_claim(artifact: ContextArtifact) -> tuple[bool, list[str]]:
    if artifact.trust_class in {TrustClass.ROOT, TrustClass.POLICY, TrustClass.EVIDENCE}:
        return True, [f"evidence-bearing source accepted: {artifact.source_type.value}"]
    return False, [
        f"{artifact.source_type.value} is derived context and cannot become source evidence by repetition"
    ]

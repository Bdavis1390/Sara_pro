from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArtifactRole(str, Enum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    LOG = "LOG"
    CONFIGURATION = "CONFIGURATION"
    SOURCE = "SOURCE"


class ArtifactEvidence(BaseModel):
    artifact_id: str = Field(min_length=1)
    role: ArtifactRole
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_type: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ComparisonOperator(str, Enum):
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LE = "LE"
    GT = "GT"
    GE = "GE"


class ExpectedResult(BaseModel):
    metric: str = Field(min_length=1)
    operator: ComparisonOperator
    target: float | int | str | bool
    units: str | None = None


class QualificationTestDefinition(BaseModel):
    test_id: str = Field(min_length=1)
    requirement_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    expected_results: list[ExpectedResult] = Field(min_length=1)
    required_artifact_roles: list[ArtifactRole] = Field(default_factory=list)

    @field_validator("required_artifact_roles")
    @classmethod
    def no_duplicate_roles(cls, value: list[ArtifactRole]) -> list[ArtifactRole]:
        if len(value) != len(set(value)):
            raise ValueError("required artifact roles must be unique")
        return value


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def artifact_from_bytes(
    *, artifact_id: str, role: ArtifactRole, data: bytes, media_type: str, locator: str
) -> ArtifactEvidence:
    return ArtifactEvidence(
        artifact_id=artifact_id,
        role=role,
        sha256=sha256_bytes(data),
        media_type=media_type,
        locator=locator,
    )


def verify_artifact(data: bytes, artifact: ArtifactEvidence) -> bool:
    return sha256_bytes(data) == artifact.sha256


def required_roles_present(
    definition: QualificationTestDefinition, artifacts: list[ArtifactEvidence]
) -> bool:
    present = {artifact.role for artifact in artifacts}
    return set(definition.required_artifact_roles).issubset(present)

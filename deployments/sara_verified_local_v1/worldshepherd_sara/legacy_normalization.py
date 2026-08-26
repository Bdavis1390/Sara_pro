from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedArtifact:
    artifact_id: str
    artifact_kind: str
    records: tuple[dict[str, Any], ...]
    source_ref: str


def normalize_legacy_artifact(artifact: dict[str, Any]) -> NormalizedArtifact:
    """Normalize one synthetic/authorized legacy artifact without inferring relationships.

    This stage preserves source identity and structure. It intentionally does not
    claim semantic extraction, SysML generation, or document understanding.
    """
    artifact_id = str(artifact["artifact_id"])
    kind = str(artifact["kind"])
    source_ref = f"artifact:{artifact_id}"

    if "rows" in artifact:
        records = tuple(dict(row) for row in artifact["rows"])
    elif "content" in artifact:
        records = ({"text": str(artifact["content"])},)
    else:
        records = ({"raw": dict(artifact)},)

    return NormalizedArtifact(
        artifact_id=artifact_id,
        artifact_kind=kind,
        records=records,
        source_ref=source_ref,
    )


def normalize_legacy_corpus(artifacts: list[dict[str, Any]]) -> tuple[NormalizedArtifact, ...]:
    seen: set[str] = set()
    normalized: list[NormalizedArtifact] = []
    for artifact in artifacts:
        item = normalize_legacy_artifact(artifact)
        if item.artifact_id in seen:
            raise ValueError(f"duplicate artifact_id: {item.artifact_id}")
        seen.add(item.artifact_id)
        normalized.append(item)
    return tuple(normalized)

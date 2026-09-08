from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, Field


EXTERNAL_BUNDLE_CLAIMS_BOUNDARY = (
    "UNCLASSIFIED NON-CONFIDENTIAL EVALUATION MATERIAL ONLY; INTERNAL SYNTHETIC SOFTWARE "
    "EVIDENCE DOES NOT ESTABLISH BAE/SDA/SSC/SPACE FORCE/GOLDEN DOME VALIDATION, "
    "OPERATIONAL MISSILE-TRACKING OR FIRE-CONTROL PERFORMANCE, CLASSIFIED READINESS, "
    "CYBER COMPLIANCE CERTIFICATION, GOVERNMENT ACCEPTANCE, OR DEPLOYMENT."
)

SAFE_RELATIVE_PATHS = frozenset(
    {
        "docs/golden_dome/GD-01_W-RMABM_CAPABILITY_BRIEF.md",
        "docs/golden_dome/GD-04_SYNTHETIC_DEMO_SPEC.md",
        "docs/golden_dome/GD-04B_G2_FAULT_CAMPAIGN_SPEC.md",
        "docs/golden_dome/GD-04C_G2B_PROVENANCE_AND_SCALE_SPEC.md",
        "docs/golden_dome/GD-04D_G2C_INTERFACE_CONFORMANCE_SPEC.md",
        "docs/golden_dome/GD-06_EVIDENCE_COMPLIANCE_GAP_REGISTER.md",
        "docs/golden_dome/GD-07_SPACE_DATA_NETWORK_CAPTURE_LANE.md",
        "docs/golden_dome/GD-08_GOLDEN_DOME_HUB_CAPABILITY_OVERVIEW.md",
        "docs/golden_dome/GD-09_G3_TRANSITION_READINESS_MAP.md",
        "docs/golden_dome/GD-10_G4_EXTERNAL_REPRODUCTION_PROTOCOL.md",
        "docs/golden_dome/GD-11_G4_EXTERNAL_EVALUATION_SCORECARD.md",
        "docs/golden_dome/GD-13_G4_EVALUATOR_HANDOFF.md",
    }
)

_EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[^\s]+"),
)


class ExternalEvidenceArtifact(BaseModel):
    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    byte_count: int = Field(ge=0)
    evidence_class: Literal["INTERNAL_SYNTHETIC_PUBLIC_SAFE_CANDIDATE"] = (
        "INTERNAL_SYNTHETIC_PUBLIC_SAFE_CANDIDATE"
    )


class ExternalEvidenceManifest(BaseModel):
    schema_version: Literal["ws-rmabm-external-bundle-v1"] = "ws-rmabm-external-bundle-v1"
    claims_boundary: str = EXTERNAL_BUNDLE_CLAIMS_BOUNDARY
    artifacts: list[ExternalEvidenceArtifact]
    manifest_sha256: str = Field(min_length=64, max_length=64)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_external_safe_candidate(*, path: str, data: bytes) -> None:
    if path not in SAFE_RELATIVE_PATHS:
        raise ValueError(f"path is not allowlisted for external candidate bundle: {path}")

    text = data.decode("utf-8")
    if _EMAIL_PATTERN.search(text):
        raise ValueError(f"external candidate contains an email address: {path}")
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"external candidate contains secret-like material: {path}")


def _canonical_manifest_payload(artifacts: list[ExternalEvidenceArtifact]) -> bytes:
    payload = {
        "schema_version": "ws-rmabm-external-bundle-v1",
        "claims_boundary": EXTERNAL_BUNDLE_CLAIMS_BOUNDARY,
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_external_evidence_manifest(
    *,
    repository_root: Path,
    relative_paths: Iterable[str],
) -> ExternalEvidenceManifest:
    """Build a deterministic manifest for explicitly allowlisted non-confidential artifacts.

    This function does not upload, submit, email, or transmit any material. The output is
    still review-required before external release.
    """
    root = repository_root.resolve()
    requested = sorted(set(str(path) for path in relative_paths))
    artifacts: list[ExternalEvidenceArtifact] = []

    for relative_path in requested:
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {relative_path}") from exc

        data = candidate.read_bytes()
        _validate_external_safe_candidate(path=relative_path, data=data)
        artifacts.append(
            ExternalEvidenceArtifact(
                path=relative_path,
                sha256=_sha256(data),
                byte_count=len(data),
            )
        )

    manifest_digest = _sha256(_canonical_manifest_payload(artifacts))
    return ExternalEvidenceManifest(artifacts=artifacts, manifest_sha256=manifest_digest)

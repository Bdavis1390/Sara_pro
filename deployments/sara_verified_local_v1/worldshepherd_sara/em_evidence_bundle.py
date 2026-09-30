"""Canonical evidence bundles for electromagnetic R&D provenance.

Bundles bind intent, candidate, validation assessment, transformation history, and
hardware/model context so two nominally similar spectra cannot be treated as
scientifically comparable unless their provenance context also matches.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .em_intelligence import EMCandidate, EMIntent
from .em_validation import EMValidationAssessment


EM_EVIDENCE_BUNDLE_SCHEMA = "worldshepherd.em-evidence-bundle.v0.1"


class EMHardwareModelContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: str = Field(min_length=1, max_length=128)
    geometry_id: str = Field(min_length=1, max_length=128)
    mesh_id: str | None = Field(default=None, max_length=128)
    solver_name: str = Field(min_length=1, max_length=128)
    solver_version: str = Field(min_length=1, max_length=128)
    solver_binary_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    config_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    hardware_revision: str | None = Field(default=None, max_length=128)
    fixture_id: str | None = Field(default=None, max_length=128)
    calibration_id: str | None = Field(default=None, max_length=128)
    environment_id: str | None = Field(default=None, max_length=128)
    notes: list[str] = Field(default_factory=list, max_length=64)


class EMTransformationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=256)
    tool_name: str = Field(min_length=1, max_length=128)
    tool_version: str | None = Field(default=None, max_length=128)
    input_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    output_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parameters_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    actor: str = Field(min_length=1, max_length=128)
    observed_utc: str = Field(min_length=1, max_length=64)


class EMCandidateEvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_EVIDENCE_BUNDLE_SCHEMA] = EM_EVIDENCE_BUNDLE_SCHEMA
    bundle_id: str = Field(min_length=1, max_length=128)
    intent: EMIntent
    candidate: EMCandidate
    validation: EMValidationAssessment
    context: EMHardwareModelContext
    transformations: list[EMTransformationStep] = Field(default_factory=list, max_length=256)
    source_receipts: list[str] = Field(default_factory=list, min_length=1, max_length=128)
    claims_boundary: list[str] = Field(default_factory=list, min_length=1, max_length=128)
    bundle_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def build_em_candidate_evidence_bundle(
    *,
    bundle_id: str,
    intent: EMIntent,
    candidate: EMCandidate,
    validation: EMValidationAssessment,
    context: EMHardwareModelContext,
    transformations: list[EMTransformationStep],
    source_receipts: list[str],
    claims_boundary: list[str],
) -> EMCandidateEvidenceBundle:
    """Build a deterministic candidate bundle and bind it to one canonical digest."""

    if validation.intent_id != intent.intent_id:
        raise ValueError("validation intent_id does not match intent")
    if validation.candidate_id != candidate.candidate_id:
        raise ValueError("validation candidate_id does not match candidate")

    if transformations:
        for previous, current in zip(transformations, transformations[1:]):
            if previous.output_digest != current.input_digest:
                raise ValueError("transformation history is not digest-contiguous")

    payload = {
        "schema_version": EM_EVIDENCE_BUNDLE_SCHEMA,
        "bundle_id": bundle_id,
        "intent": intent.model_dump(mode="json"),
        "candidate": candidate.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
        "context": context.model_dump(mode="json"),
        "transformations": [step.model_dump(mode="json") for step in transformations],
        "source_receipts": source_receipts,
        "claims_boundary": claims_boundary,
    }

    return EMCandidateEvidenceBundle(
        **payload,
        bundle_digest=_digest(payload),
    )


def verify_em_candidate_evidence_bundle(bundle: EMCandidateEvidenceBundle) -> bool:
    payload = bundle.model_dump(mode="json", exclude={"bundle_digest"})
    return bundle.bundle_digest == _digest(payload)

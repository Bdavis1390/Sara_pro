"""Synthetic FMISO interpretation/provenance contract for research-only handoff.

NO patient images, clinical cutoff, real tracer inference, radiotherapy dose,
TPS export, trained reader identity verification, or authorization is performed.

The 2024 FMISO interreader study (PMID 39266287) reported that specialist
training can materially improve agreement. It does NOT supply universal
clinical thresholds or establish that any supplied synthetic readers are real.
This module checks *declared* metadata completeness and reader concordance.
Source digests and training flags are self-reported, not authenticated.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Literal

from .closed_loop import AdaptationThresholds, BiologicalState
from .research_objective_intent import (
    ResearchObjectiveIntent,
    ResearchPriorityPolicy,
    make_synthetic_research_objective_intent,
)

_S256 = re.compile(r"^[0-9a-f]{64}$")
_SYN = re.compile(r"^SYN-[A-Z0-9_-]{1,32}$")
Interpretation = Literal["positive", "negative", "indeterminate"]


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _sha(name: str, value: str) -> None:
    if not isinstance(value, str) or _S256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


@dataclass(frozen=True)
class DeclaredReader:
    reader_token: str
    trained_for_locked_protocol: bool
    interpretation: Interpretation

    def validate(self) -> None:
        if not isinstance(self.reader_token, str) or _SYN.fullmatch(self.reader_token) is None:
            raise ValueError("reader_token must be a SYN- research-only token")
        if type(self.trained_for_locked_protocol) is not bool:
            raise ValueError("trained_for_locked_protocol must be boolean")
        if self.interpretation not in ("positive", "negative", "indeterminate"):
            raise ValueError("invalid interpretation")


@dataclass(frozen=True)
class DeclaredFMISOObservation:
    """Invented/synthetic metadata, NEVER a patient imaging record."""

    phase_index: int
    study_token: str
    tracer: str
    image_sha256: str
    acquisition_protocol_sha256: str
    quantification_protocol_sha256: str
    reference_frame_sha256: str
    registration_independently_reviewed: bool
    readers: tuple[DeclaredReader, DeclaredReader]

    def validate(self) -> None:
        if type(self.phase_index) is not int or self.phase_index < 0:
            raise ValueError("phase_index must be a nonnegative integer")
        if not isinstance(self.study_token, str) or _SYN.fullmatch(self.study_token) is None:
            raise ValueError("study_token must be a SYN- research-only token")
        if self.tracer != "18F-FMISO":
            raise ValueError("tracer must be exactly 18F-FMISO; FDG is not interchangeable")
        for name in ("image_sha256", "acquisition_protocol_sha256",
                     "quantification_protocol_sha256", "reference_frame_sha256"):
            _sha(name, getattr(self, name))
        if type(self.registration_independently_reviewed) is not bool:
            raise ValueError("registration_independently_reviewed must be boolean")
        if not isinstance(self.readers, tuple) or len(self.readers) != 2:
            raise ValueError("require two synthetic reader declarations")
        for reader in self.readers:
            if not isinstance(reader, DeclaredReader):
                raise ValueError("readers must be DeclaredReader instances")
            reader.validate()
        if self.readers[0].reader_token == self.readers[1].reader_token:
            raise ValueError("reader tokens must be distinct")


@dataclass(frozen=True)
class AssayEligibility:
    eligible: bool
    blockers: tuple[str, ...]
    declared_metadata_sha256: str
    independently_validated: bool = False


@dataclass(frozen=True)
class FMISOResearchHandoff:
    assay: AssayEligibility
    intent: ResearchObjectiveIntent


def assess_declared_fmiso_pair(
    previous: DeclaredFMISOObservation,
    current: DeclaredFMISOObservation,
) -> AssayEligibility:
    """Fail closed on declared temporal/reader/protocol inconsistency.

    This checks metadata, not image content, physician credentials, tracer
    quantification, clinical reproducibility, or independent source custody.
    """
    previous.validate()
    current.validate()
    if current.phase_index <= previous.phase_index:
        raise ValueError("FMISO phases must advance")
    blockers: list[str] = []
    if previous.study_token != current.study_token:
        blockers.append("different_research_study")
    if previous.image_sha256 == current.image_sha256:
        blockers.append("duplicate_image_digest")
    for field in ("acquisition_protocol_sha256", "quantification_protocol_sha256",
                  "reference_frame_sha256"):
        if getattr(previous, field) != getattr(current, field):
            blockers.append(f"{field}_mismatch")
    for name, observation in (("previous", previous), ("current", current)):
        if not observation.registration_independently_reviewed:
            blockers.append(f"{name}_registration_not_reviewed")
        if not all(r.trained_for_locked_protocol for r in observation.readers):
            blockers.append(f"{name}_reader_training_unconfirmed")
        opinions = tuple(r.interpretation for r in observation.readers)
        if "indeterminate" in opinions:
            blockers.append(f"{name}_interpretation_indeterminate")
        elif len(set(opinions)) > 1:
            blockers.append(f"{name}_reader_disagreement")
    data = {
        "previous": {
            "phase": previous.phase_index,
            "study": previous.study_token,
            "tracer": previous.tracer,
            "image": previous.image_sha256,
            "acquisition": previous.acquisition_protocol_sha256,
            "quantification": previous.quantification_protocol_sha256,
            "reference": previous.reference_frame_sha256,
            "registration_declared": previous.registration_independently_reviewed,
            "readers": [
                (r.reader_token, r.trained_for_locked_protocol, r.interpretation)
                for r in previous.readers
            ],
        },
        "current": {
            "phase": current.phase_index,
            "study": current.study_token,
            "tracer": current.tracer,
            "image": current.image_sha256,
            "acquisition": current.acquisition_protocol_sha256,
            "quantification": current.quantification_protocol_sha256,
            "reference": current.reference_frame_sha256,
            "registration_declared": current.registration_independently_reviewed,
            "readers": [
                (r.reader_token, r.trained_for_locked_protocol, r.interpretation)
                for r in current.readers
            ],
        },
    }
    return AssayEligibility(
        eligible=not blockers,
        blockers=tuple(blockers),
        declared_metadata_sha256=_digest(data),
        independently_validated=False,
    )


def mock_fmiso_research_handoff(
    *,
    previous: BiologicalState,
    current: BiologicalState,
    previous_fmiso: DeclaredFMISOObservation,
    current_fmiso: DeclaredFMISOObservation,
    thresholds: AdaptationThresholds,
    policy: ResearchPriorityPolicy,
    region_ids: tuple[str, ...],
) -> FMISOResearchHandoff:
    """Only a mock pre-TPS adapter; it cannot authorize a clinical plan."""
    previous.validate()
    current.validate()
    if (previous.phase_index != previous_fmiso.phase_index
            or current.phase_index != current_fmiso.phase_index):
        raise ValueError("biological and mock FMISO phases do not match")
    # Validate research-policy inputs regardless of assay eligibility; fail
    # closed on malformed policy rather than silently accepting it.
    thresholds.validate()
    policy.validate()
    assay = assess_declared_fmiso_pair(previous_fmiso, current_fmiso)
    if not assay.eligible:
        return FMISOResearchHandoff(
            assay=assay,
            intent=ResearchObjectiveIntent(
                intended_use="SYNTHETIC_PRE_TPS_OBJECTIVE_REVIEW_ONLY",
                decision_action="HOLD_LAST_VALID",
                synthetic_policy_only=True,
                proposal_allowed=False,
                treatment_authority=False,
                dose_or_prescription_defined=False,
                tps_export_allowed=False,
                region_priorities=(),
                next_step="declared FMISO assay evidence disqualified: "
                + ", ".join(assay.blockers)
                + "; independent clinician review required, no patient use",
            ),
        )
    return FMISOResearchHandoff(
        assay=assay,
        intent=make_synthetic_research_objective_intent(
            previous=previous,
            current=current,
            thresholds=thresholds,
            policy=policy,
            region_ids=region_ids,
        ),
    )

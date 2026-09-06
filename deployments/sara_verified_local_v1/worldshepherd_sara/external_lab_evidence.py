from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

LAB_EVIDENCE_SCHEMA_VERSION = "ws-lab-evidence-package-1"
_SHA256_PATTERN = r"^sha256:[0-9a-fA-F]{64}$"


class LaboratoryIndependence(str, Enum):
    INTERNAL = "internal"
    EXTERNAL_NONINDEPENDENT = "external_nonindependent"
    EXTERNAL_INDEPENDENCE_PENDING = "external_independence_pending"
    EXTERNAL_INDEPENDENT_REVIEWED = "external_independent_reviewed"


class EvidenceFile(BaseModel):
    file_id: str = Field(min_length=1, max_length=256)
    role: Literal[
        "raw_data",
        "calibration",
        "method",
        "processed_data",
        "analysis",
        "report",
        "image",
        "other",
    ]
    sha256: str = Field(pattern=_SHA256_PATTERN)
    media_type: str = Field(min_length=1, max_length=256)
    original_name: str | None = Field(default=None, max_length=512)
    source_system: str | None = Field(default=None, max_length=256)
    generated_at_utc: str | None = Field(default=None, max_length=128)


class LaboratoryInstrument(BaseModel):
    instrument_id: str = Field(min_length=1, max_length=256)
    instrument_type: str = Field(min_length=1, max_length=256)
    manufacturer: str | None = Field(default=None, max_length=256)
    model: str | None = Field(default=None, max_length=256)
    serial_or_asset_id: str | None = Field(default=None, max_length=256)
    software_or_firmware: str | None = Field(default=None, max_length=256)
    calibration_record_ids: list[str] = Field(default_factory=list)
    calibration_due_or_valid_at_test: bool | None = None


class CustodyEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=256)
    timestamp_utc: str = Field(min_length=1, max_length=128)
    actor_or_org: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=1024)
    location_or_system: str | None = Field(default=None, max_length=512)


class LaboratorySample(BaseModel):
    sample_id: str = Field(min_length=1, max_length=256)
    parent_build_id: str | None = Field(default=None, max_length=256)
    specimen_type: str = Field(min_length=1, max_length=256)
    orientation: str | None = Field(default=None, max_length=256)
    coordinate_or_location: str | None = Field(default=None, max_length=512)
    configuration_digest: str = Field(pattern=_SHA256_PATTERN)
    custody_events: list[CustodyEvent] = Field(min_length=1)


class LaboratoryMethod(BaseModel):
    method_id: str = Field(min_length=1, max_length=256)
    title: str = Field(min_length=1, max_length=1024)
    standard_or_procedure_ref: str | None = Field(default=None, max_length=512)
    revision: str | None = Field(default=None, max_length=128)
    deviations: list[str] = Field(default_factory=list)


class LaboratoryResult(BaseModel):
    result_id: str = Field(min_length=1, max_length=256)
    sample_id: str = Field(min_length=1, max_length=256)
    observable: str = Field(min_length=1, max_length=512)
    value: float | int | str | None = None
    unit: str | None = Field(default=None, max_length=128)
    uncertainty: str | None = Field(default=None, max_length=512)
    method_id: str = Field(min_length=1, max_length=256)
    source_file_ids: list[str] = Field(min_length=1)
    pass_fail_interpretation: str | None = Field(default=None, max_length=1024)


class ExternalLaboratoryEvidencePackage(BaseModel):
    schema_version: str = Field(
        default=LAB_EVIDENCE_SCHEMA_VERSION,
        pattern=r"^ws-lab-evidence-package-1$",
    )
    package_id: str = Field(min_length=1, max_length=256)
    campaign_id: str = Field(min_length=1, max_length=256)
    project_id: str = Field(min_length=1, max_length=256)
    artifact_id: str = Field(min_length=1, max_length=256)
    laboratory_organization: str = Field(min_length=1, max_length=512)
    facility: str = Field(min_length=1, max_length=512)
    engagement_reference: str | None = Field(default=None, max_length=512)
    received_at_utc: str = Field(min_length=1, max_length=128)
    acquisition_start_utc: str = Field(min_length=1, max_length=128)
    acquisition_end_utc: str = Field(min_length=1, max_length=128)
    time_reference: str = Field(min_length=1, max_length=128)
    independence: LaboratoryIndependence
    independence_basis: str = Field(min_length=1, max_length=2048)
    samples: list[LaboratorySample] = Field(min_length=1)
    instruments: list[LaboratoryInstrument] = Field(min_length=1)
    methods: list[LaboratoryMethod] = Field(min_length=1)
    files: list[EvidenceFile] = Field(min_length=1)
    results: list[LaboratoryResult] = Field(default_factory=list)
    laboratory_report_reference: str | None = Field(default=None, max_length=512)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> "ExternalLaboratoryEvidencePackage":
        sample_ids = [item.sample_id for item in self.samples]
        method_ids = [item.method_id for item in self.methods]
        file_ids = [item.file_id for item in self.files]
        instrument_ids = [item.instrument_id for item in self.instruments]

        for label, values in {
            "sample": sample_ids,
            "method": method_ids,
            "file": file_ids,
            "instrument": instrument_ids,
        }.items():
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label} IDs are not permitted")

        sample_set = set(sample_ids)
        method_set = set(method_ids)
        file_set = set(file_ids)
        for result in self.results:
            if result.sample_id not in sample_set:
                raise ValueError(f"result references unknown sample_id: {result.sample_id}")
            if result.method_id not in method_set:
                raise ValueError(f"result references unknown method_id: {result.method_id}")
            unknown_files = set(result.source_file_ids) - file_set
            if unknown_files:
                raise ValueError(
                    "result references unknown source_file_ids: "
                    + ", ".join(sorted(unknown_files))
                )
        return self

    def canonical_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()


def assess_lab_package(
    package: ExternalLaboratoryEvidencePackage,
) -> dict[str, object]:
    """Assess evidence completeness without promoting scientific maturity."""
    blockers: list[str] = []
    warnings: list[str] = []

    raw_files = [item for item in package.files if item.role == "raw_data"]
    calibration_files = [item for item in package.files if item.role == "calibration"]
    if not raw_files:
        blockers.append("NO_RAW_DATA_FILES")

    instruments_without_calibration = [
        item.instrument_id
        for item in package.instruments
        if not item.calibration_record_ids
    ]
    if instruments_without_calibration:
        blockers.append("MISSING_INSTRUMENT_CALIBRATION_REFS")

    invalid_at_test = [
        item.instrument_id
        for item in package.instruments
        if item.calibration_due_or_valid_at_test is False
    ]
    if invalid_at_test:
        blockers.append("CALIBRATION_NOT_VALID_AT_TEST")

    unknown_calibration_state = [
        item.instrument_id
        for item in package.instruments
        if item.calibration_due_or_valid_at_test is None
    ]
    if unknown_calibration_state:
        warnings.append("CALIBRATION_VALIDITY_NOT_DECLARED")

    if not calibration_files:
        warnings.append("NO_CALIBRATION_FILES_EMBEDDED")

    if not package.results:
        warnings.append("NO_STRUCTURED_RESULTS")

    if package.independence == LaboratoryIndependence.EXTERNAL_INDEPENDENT_REVIEWED:
        if not package.engagement_reference:
            blockers.append("INDEPENDENCE_REVIEW_REQUIRES_ENGAGEMENT_REFERENCE")

    return {
        "package_digest": package.canonical_digest(),
        "evidence_complete": not blockers,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "raw_file_count": len(raw_files),
        "sample_count": len(package.samples),
        "instrument_count": len(package.instruments),
        "result_count": len(package.results),
        "independence": package.independence.value,
        "maturity_promoted": False,
        "status_note": (
            "Package is structurally suitable for scientific review; maturity remains unchanged until PVK review and applicable replication gates close."
            if not blockers
            else "Package is incomplete for scientific review; maturity remains unchanged."
        ),
    }

"""Fail-closed DICOM-RT validation helpers for BAROS research workflows.

NON-CLINICAL. This module validates a deliberately narrow subset of RTSTRUCT,
RTPLAN, and RTDOSE semantics before research use. Passing these checks is not
DICOM conformance certification, TPS interoperability proof, dose validation,
or evidence of clinical safety/effectiveness.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.uid import RTDoseStorage, RTPlanStorage, RTStructureSetStorage


SUPPORTED_RT_SOPS = {
    str(RTStructureSetStorage): ("RTSTRUCT", "RTSTRUCT"),
    str(RTPlanStorage): ("RTPLAN", "RTPLAN"),
    str(RTDoseStorage): ("RTDOSE", "RTDOSE"),
}


@dataclass(frozen=True)
class DicomRTValidationReport:
    valid: bool
    kind: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def require_valid(self) -> None:
        if not self.valid:
            raise ValueError("DICOM-RT validation failed: " + "; ".join(self.errors))


def _text(ds: Dataset, keyword: str) -> str | None:
    value = getattr(ds, keyword, None)
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _require_text(ds: Dataset, keyword: str, errors: list[str]) -> str | None:
    value = _text(ds, keyword)
    if value is None:
        errors.append(f"missing/empty required attribute: {keyword}")
    return value


def _require_sequence(ds: Dataset, keyword: str, errors: list[str], *, allow_empty: bool = False) -> None:
    if not hasattr(ds, keyword):
        errors.append(f"missing required sequence: {keyword}")
        return
    sequence = getattr(ds, keyword)
    if sequence is None or (not allow_empty and len(sequence) == 0):
        errors.append(f"empty required sequence: {keyword}")


def _validate_common(ds: Dataset, errors: list[str]) -> tuple[str | None, str | None]:
    sop_class = _require_text(ds, "SOPClassUID", errors)
    _require_text(ds, "SOPInstanceUID", errors)
    _require_text(ds, "StudyInstanceUID", errors)
    _require_text(ds, "SeriesInstanceUID", errors)
    modality = _require_text(ds, "Modality", errors)

    if sop_class and sop_class not in SUPPORTED_RT_SOPS:
        errors.append(f"unsupported SOPClassUID: {sop_class}")
        return sop_class, modality

    if sop_class in SUPPORTED_RT_SOPS and modality:
        expected_modality = SUPPORTED_RT_SOPS[sop_class][1]
        if modality != expected_modality:
            errors.append(
                f"Modality {modality!r} does not match SOPClassUID; expected {expected_modality!r}"
            )
    return sop_class, modality


def _validate_rtstruct(ds: Dataset, errors: list[str], warnings: list[str]) -> None:
    _require_text(ds, "StructureSetLabel", errors)
    _require_text(ds, "StructureSetDate", errors)
    _require_text(ds, "StructureSetTime", errors)
    _require_sequence(ds, "ReferencedFrameOfReferenceSequence", errors)
    _require_sequence(ds, "StructureSetROISequence", errors)
    _require_sequence(ds, "ROIContourSequence", errors)
    _require_sequence(ds, "RTROIObservationsSequence", errors)

    roi_numbers: set[int] = set()
    for item in getattr(ds, "StructureSetROISequence", []):
        if not hasattr(item, "ROINumber"):
            errors.append("StructureSetROISequence item missing ROINumber")
            continue
        roi_numbers.add(int(item.ROINumber))
        if not _text(item, "ROIName"):
            errors.append(f"ROI {item.ROINumber} missing ROIName")

    contour_refs = {
        int(item.ReferencedROINumber)
        for item in getattr(ds, "ROIContourSequence", [])
        if hasattr(item, "ReferencedROINumber")
    }
    observation_refs = {
        int(item.ReferencedROINumber)
        for item in getattr(ds, "RTROIObservationsSequence", [])
        if hasattr(item, "ReferencedROINumber")
    }
    if contour_refs - roi_numbers:
        errors.append("ROIContourSequence references undefined ROI number(s)")
    if observation_refs - roi_numbers:
        errors.append("RTROIObservationsSequence references undefined ROI number(s)")
    if roi_numbers - contour_refs:
        warnings.append("one or more defined ROIs have no ROIContourSequence reference")


def _validate_rtplan(ds: Dataset, errors: list[str], warnings: list[str]) -> None:
    _require_text(ds, "RTPlanLabel", errors)
    geometry = _require_text(ds, "RTPlanGeometry", errors)
    if geometry not in {None, "PATIENT", "TREATMENT_DEVICE"}:
        errors.append(f"unsupported RTPlanGeometry: {geometry!r}")
    if geometry == "PATIENT":
        _require_sequence(ds, "ReferencedStructureSetSequence", errors)
        for item in getattr(ds, "ReferencedStructureSetSequence", []):
            ref_class = _require_text(item, "ReferencedSOPClassUID", errors)
            _require_text(item, "ReferencedSOPInstanceUID", errors)
            if ref_class and ref_class != str(RTStructureSetStorage):
                errors.append("RTPLAN referenced structure set has wrong SOP class")
    if not hasattr(ds, "FractionGroupSequence"):
        warnings.append("RTPLAN has no FractionGroupSequence; bounded research use only")


def _validate_rtdose(ds: Dataset, errors: list[str], warnings: list[str]) -> None:
    units = _require_text(ds, "DoseUnits", errors)
    if units not in {None, "GY", "RELATIVE"}:
        errors.append(f"unsupported DoseUnits: {units!r}")
    dose_type = _require_text(ds, "DoseType", errors)
    if dose_type not in {None, "PHYSICAL", "EFFECTIVE", "ERROR"}:
        errors.append(f"unsupported DoseType: {dose_type!r}")
    _require_text(ds, "DoseSummationType", errors)
    scaling = getattr(ds, "DoseGridScaling", None)
    try:
        scaling_value = float(scaling)
        if not np.isfinite(scaling_value) or scaling_value <= 0.0:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("DoseGridScaling must be finite and positive")

    for keyword in (
        "Rows",
        "Columns",
        "BitsAllocated",
        "BitsStored",
        "HighBit",
        "PixelRepresentation",
        "SamplesPerPixel",
        "PhotometricInterpretation",
        "PixelData",
    ):
        if not hasattr(ds, keyword):
            errors.append(f"missing RTDOSE pixel attribute: {keyword}")

    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    if frames > 1:
        offsets = getattr(ds, "GridFrameOffsetVector", None)
        if offsets is None or len(offsets) != frames:
            errors.append("multi-frame RTDOSE requires GridFrameOffsetVector matching NumberOfFrames")

    if units == "RELATIVE":
        warnings.append("relative RTDOSE cannot be interpreted as absolute Gy")


def validate_rt_dataset(ds: Dataset, *, expected_kind: str | None = None) -> DicomRTValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    sop_class, _ = _validate_common(ds, errors)
    kind = SUPPORTED_RT_SOPS.get(sop_class, (None, None))[0] if sop_class else None

    if expected_kind is not None and kind != expected_kind:
        errors.append(f"expected {expected_kind}, got {kind or 'unsupported/unknown'}")

    if kind == "RTSTRUCT":
        _validate_rtstruct(ds, errors, warnings)
    elif kind == "RTPLAN":
        _validate_rtplan(ds, errors, warnings)
    elif kind == "RTDOSE":
        _validate_rtdose(ds, errors, warnings)

    return DicomRTValidationReport(not errors, kind, tuple(errors), tuple(warnings))


def read_validated_rt(path: str | Path, *, expected_kind: str | None = None) -> Dataset:
    """Read a DICOM file and reject unsupported or malformed bounded RT objects."""
    ds = dcmread(str(path), force=False)
    report = validate_rt_dataset(ds, expected_kind=expected_kind)
    report.require_valid()
    return ds


def decode_rtdose(ds: Dataset, *, require_absolute_gy: bool = True) -> np.ndarray:
    """Decode validated RTDOSE pixels and apply DoseGridScaling.

    The returned array is a numerical research representation only. This does
    not establish physical-dose correctness or clinical suitability.
    """
    report = validate_rt_dataset(ds, expected_kind="RTDOSE")
    report.require_valid()
    if require_absolute_gy and str(ds.DoseUnits) != "GY":
        raise ValueError("absolute-Gy decoding requires DoseUnits == 'GY'")
    raw = np.asarray(ds.pixel_array, dtype=np.float64)
    scaled = raw * float(ds.DoseGridScaling)
    if not np.all(np.isfinite(scaled)):
        raise ValueError("decoded dose contains non-finite values")
    return scaled


def validate_linkage(rtstruct: Dataset, rtplan: Dataset, rtdose: Dataset) -> tuple[bool, tuple[str, ...]]:
    """Check a bounded cross-object reference chain for synthetic/research use."""
    errors: list[str] = []
    for ds, kind in ((rtstruct, "RTSTRUCT"), (rtplan, "RTPLAN"), (rtdose, "RTDOSE")):
        report = validate_rt_dataset(ds, expected_kind=kind)
        errors.extend(f"{kind}: {message}" for message in report.errors)

    struct_uid = _text(rtstruct, "SOPInstanceUID")
    plan_uid = _text(rtplan, "SOPInstanceUID")

    plan_refs: set[str] = set()
    for item in getattr(rtplan, "ReferencedStructureSetSequence", []):
        ref = _text(item, "ReferencedSOPInstanceUID")
        if ref:
            plan_refs.add(ref)
    if struct_uid and struct_uid not in plan_refs:
        errors.append("RTPLAN does not reference the supplied RTSTRUCT SOPInstanceUID")

    dose_plan_refs: set[str] = set()
    for item in getattr(rtdose, "ReferencedRTPlanSequence", []):
        ref = _text(item, "ReferencedSOPInstanceUID")
        if ref:
            dose_plan_refs.add(ref)
    if plan_uid and plan_uid not in dose_plan_refs:
        errors.append("RTDOSE does not reference the supplied RTPLAN SOPInstanceUID")

    studies = {_text(ds, "StudyInstanceUID") for ds in (rtstruct, rtplan, rtdose)}
    if None in studies or len(studies) != 1:
        errors.append("RTSTRUCT/RTPLAN/RTDOSE StudyInstanceUID values do not match")

    return (not errors, tuple(errors))

import numpy as np
import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import (
    ExplicitVRLittleEndian,
    RTDoseStorage,
    RTPlanStorage,
    RTStructureSetStorage,
)

from baros.dicom_rt import decode_rtdose, read_validated_rt, validate_linkage, validate_rt_dataset


STUDY_UID = "1.2.826.0.1.3680043.10.543.100"
STRUCT_UID = "1.2.826.0.1.3680043.10.543.101"
PLAN_UID = "1.2.826.0.1.3680043.10.543.102"
DOSE_UID = "1.2.826.0.1.3680043.10.543.103"
FRAME_UID = "1.2.826.0.1.3680043.10.543.104"


def _file_dataset(sop_class, sop_instance, modality, series_suffix):
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = sop_class
    meta.MediaStorageSOPInstanceUID = sop_instance
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = sop_class
    ds.SOPInstanceUID = sop_instance
    ds.StudyInstanceUID = STUDY_UID
    ds.SeriesInstanceUID = f"1.2.826.0.1.3680043.10.543.{series_suffix}"
    ds.Modality = modality
    ds.PatientName = "SYNTHETIC^BAROS"
    ds.PatientID = "SYNTHETIC-ONLY"
    return ds


def synthetic_rtstruct():
    ds = _file_dataset(RTStructureSetStorage, STRUCT_UID, "RTSTRUCT", 201)
    ds.StructureSetLabel = "BAROS_SYN"
    ds.StructureSetDate = "20260915"
    ds.StructureSetTime = "120000"

    frame = Dataset()
    frame.FrameOfReferenceUID = FRAME_UID
    ds.ReferencedFrameOfReferenceSequence = Sequence([frame])

    roi = Dataset()
    roi.ROINumber = 1
    roi.ROIName = "SYNTHETIC_PTV"
    roi.ReferencedFrameOfReferenceUID = FRAME_UID
    roi.ROIGenerationAlgorithm = "MANUAL"
    ds.StructureSetROISequence = Sequence([roi])

    contour = Dataset()
    contour.ReferencedROINumber = 1
    contour.ROIDisplayColor = [255, 0, 0]
    contour.ContourSequence = Sequence([])
    ds.ROIContourSequence = Sequence([contour])

    obs = Dataset()
    obs.ObservationNumber = 1
    obs.ReferencedROINumber = 1
    obs.RTROIInterpretedType = "PTV"
    obs.ROIInterpreter = ""
    ds.RTROIObservationsSequence = Sequence([obs])
    return ds


def synthetic_rtplan():
    ds = _file_dataset(RTPlanStorage, PLAN_UID, "RTPLAN", 202)
    ds.RTPlanLabel = "BAROS_SYN"
    ds.RTPlanDate = "20260915"
    ds.RTPlanTime = "120000"
    ds.RTPlanGeometry = "PATIENT"

    ref = Dataset()
    ref.ReferencedSOPClassUID = RTStructureSetStorage
    ref.ReferencedSOPInstanceUID = STRUCT_UID
    ds.ReferencedStructureSetSequence = Sequence([ref])

    fraction = Dataset()
    fraction.FractionGroupNumber = 1
    fraction.NumberOfFractionsPlanned = 1
    fraction.NumberOfBeams = 0
    fraction.NumberOfBrachyApplicationSetups = 0
    ds.FractionGroupSequence = Sequence([fraction])
    return ds


def synthetic_rtdose():
    ds = _file_dataset(RTDoseStorage, DOSE_UID, "RTDOSE", 203)
    ds.DoseUnits = "GY"
    ds.DoseType = "PHYSICAL"
    ds.DoseSummationType = "PLAN"
    ds.DoseGridScaling = 0.01
    ds.Rows = 2
    ds.Columns = 2
    ds.NumberOfFrames = 2
    ds.GridFrameOffsetVector = [0.0, 2.5]
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelSpacing = [2.5, 2.5]
    ds.ImagePositionPatient = [0.0, 0.0, 0.0]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    pixels = np.array([[[100, 200], [300, 400]], [[500, 600], [700, 800]]], dtype="<u2")
    ds.PixelData = pixels.tobytes()

    ref = Dataset()
    ref.ReferencedSOPClassUID = RTPlanStorage
    ref.ReferencedSOPInstanceUID = PLAN_UID
    ds.ReferencedRTPlanSequence = Sequence([ref])
    return ds


def test_supported_rt_objects_validate_and_link():
    rtstruct = synthetic_rtstruct()
    rtplan = synthetic_rtplan()
    rtdose = synthetic_rtdose()
    assert validate_rt_dataset(rtstruct, expected_kind="RTSTRUCT").valid
    assert validate_rt_dataset(rtplan, expected_kind="RTPLAN").valid
    assert validate_rt_dataset(rtdose, expected_kind="RTDOSE").valid
    ok, errors = validate_linkage(rtstruct, rtplan, rtdose)
    assert ok, errors


def test_rtdose_decoding_applies_scaling():
    decoded = decode_rtdose(synthetic_rtdose())
    assert decoded.shape == (2, 2, 2)
    assert decoded[0, 0, 0] == pytest.approx(1.0)
    assert decoded[-1, -1, -1] == pytest.approx(8.0)


def test_round_trip_file_read_is_validated(tmp_path):
    path = tmp_path / "synthetic_rtdose.dcm"
    synthetic_rtdose().save_as(path, enforce_file_format=True)
    loaded = read_validated_rt(path, expected_kind="RTDOSE")
    assert str(loaded.SOPInstanceUID) == DOSE_UID
    assert decode_rtdose(loaded)[1, 0, 0] == pytest.approx(5.0)


def test_wrong_modality_fails_closed():
    ds = synthetic_rtdose()
    ds.Modality = "CT"
    report = validate_rt_dataset(ds, expected_kind="RTDOSE")
    assert not report.valid
    assert any("does not match SOPClassUID" in error for error in report.errors)


def test_missing_dose_scaling_fails_closed():
    ds = synthetic_rtdose()
    del ds.DoseGridScaling
    report = validate_rt_dataset(ds, expected_kind="RTDOSE")
    assert not report.valid
    with pytest.raises(ValueError):
        decode_rtdose(ds)


def test_cross_object_uid_mismatch_fails_closed():
    rtstruct = synthetic_rtstruct()
    rtplan = synthetic_rtplan()
    rtdose = synthetic_rtdose()
    rtplan.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID = "1.2.826.0.1.3680043.10.543.999"
    ok, errors = validate_linkage(rtstruct, rtplan, rtdose)
    assert not ok
    assert any("does not reference the supplied RTSTRUCT" in error for error in errors)


def test_relative_dose_is_not_decoded_as_absolute_gy():
    ds = synthetic_rtdose()
    ds.DoseUnits = "RELATIVE"
    report = validate_rt_dataset(ds, expected_kind="RTDOSE")
    assert report.valid
    assert report.warnings
    with pytest.raises(ValueError):
        decode_rtdose(ds, require_absolute_gy=True)

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from worldshepherd_sara.sda import (
    SdaContractValidationState,
    SdaInterfaceContract,
    SdaSourceClass,
    SdaSourceIdentity,
)
from worldshepherd_sara.sda_canonical import (
    SdaCanonicalEnvelope,
    SdaCanonicalStateVector,
    SdaCanonicalTimeTag,
    SdaObjectIdentity,
    opm_profile_to_canonical_envelope,
    source_text_sha256,
    tdm_range_profile_to_canonical_envelopes,
)
from worldshepherd_sara.sda_ccsds import (
    parse_opm_v3_kvn_profile,
    parse_tdm_v2_range_kvn_profile,
)


OPM = """CCSDS_OPM_VERS = 3.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
MESSAGE_ID = WS-CANONICAL-OPM-001
OBJECT_NAME = WS-SYNTH-OBJECT
OBJECT_ID = 2026-999A
CENTER_NAME = EARTH
REF_FRAME = GCRF
TIME_SYSTEM = UTC
EPOCH = 2026-09-18T00:00:01
X = 7000.0 [km]
Y = -1200.5 [km]
Z = 350.25 [km]
X_DOT = 0.1 [km/s]
Y_DOT = 7.4 [km/s]
Z_DOT = -0.3 [km/s]
"""


OPM_WITH_COVARIANCE = OPM + """COV_REF_FRAME = RTN
CX_X = 4.0 [km**2]
CY_X = 0.0 [km**2]
CY_Y = 9.0 [km**2]
CZ_X = 0.0 [km**2]
CZ_Y = 0.0 [km**2]
CZ_Z = 16.0 [km**2]
CX_DOT_X = 0.0 [km**2/s]
CX_DOT_Y = 0.0 [km**2/s]
CX_DOT_Z = 0.0 [km**2/s]
CX_DOT_X_DOT = 0.04 [km**2/s**2]
CY_DOT_X = 0.0 [km**2/s]
CY_DOT_Y = 0.0 [km**2/s]
CY_DOT_Z = 0.0 [km**2/s]
CY_DOT_X_DOT = 0.0 [km**2/s**2]
CY_DOT_Y_DOT = 0.05 [km**2/s**2]
CZ_DOT_X = 0.0 [km**2/s]
CZ_DOT_Y = 0.0 [km**2/s]
CZ_DOT_Z = 0.0 [km**2/s]
CZ_DOT_X_DOT = 0.0 [km**2/s**2]
CZ_DOT_Y_DOT = 0.0 [km**2/s**2]
CZ_DOT_Z_DOT = 0.06 [km**2/s**2]
"""


TDM = """CCSDS_TDM_VERS = 2.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
MESSAGE_ID = WS-CANONICAL-TDM-001
META_START
TIME_SYSTEM = UTC
PARTICIPANT_1 = WS-SYNTH-STATION
PARTICIPANT_2 = WS-SYNTH-OBJECT
MODE = SEQUENTIAL
PATH = 1,2,1
RANGE_UNITS = km
META_STOP
DATA_START
RANGE = 2026-09-18T00:00:01 1234.5
RANGE = 2026-09-18T00:00:02 1234.75
DATA_STOP
"""


RECEIVED = datetime(2026, 9, 18, 0, 0, 3, tzinfo=timezone.utc)


def source() -> SdaSourceIdentity:
    return SdaSourceIdentity(
        source_id="CCSDS-SYNTH-A",
        source_class=SdaSourceClass.SYNTHETIC,
        provider="Worldshepherd synthetic CCSDS fixture",
        sensor_id="CCSDS-FIXTURE-1",
        adapter_id="WS-SDA-CCSDS",
        adapter_version="g4a",
    )


def contract() -> SdaInterfaceContract:
    return SdaInterfaceContract(
        contract_id="SDA-CCSDS-G4A-CONTRACT",
        source_id="CCSDS-SYNTH-A",
        adapter_id="WS-SDA-CCSDS",
        adapter_version="g4a",
        authoritative_spec_ref="CCSDS 502.0-B-3 / 503.0-B-2",
        authoritative_spec_digest="sha256:" + "e" * 64,
        allowed_reference_frames=["GCRF"],
        allowed_releasability_tags=["US_ONLY"],
        max_age_seconds=600.0,
        max_future_skew_seconds=30.0,
        max_clock_uncertainty_seconds=1.0,
        validation_state=SdaContractValidationState.SYNTHETIC,
        validation_ref="test://ws-sda-ccsds-g4a",
        enabled=True,
    )


def covariance():
    matrix = [[0.0 for _ in range(6)] for _ in range(6)]
    for index in range(3):
        matrix[index][index] = 1.0
    for index in range(3, 6):
        matrix[index][index] = 0.01
    return matrix


def test_opm_canonicalization_preserves_object_center_time_and_state_without_inventing_covariance():
    parsed = parse_opm_v3_kvn_profile(OPM)
    envelope = opm_profile_to_canonical_envelope(
        parsed,
        observation_id="CCSDS-OPM-OBS-001",
        source_event_id="CCSDS-OPM-EVENT-001",
        source_sequence=1,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(OPM),
        received_at=RECEIVED,
    )

    assert envelope.object_identity is not None
    assert envelope.object_identity.object_id == "2026-999A"
    assert envelope.object_identity.object_name == "WS-SYNTH-OBJECT"
    assert envelope.object_identity.center_name == "EARTH"
    assert envelope.time_tag.raw == "2026-09-18T00:00:01"
    assert envelope.time_tag.time_system == "UTC"
    assert envelope.time_tag.normalized_utc is not None
    assert envelope.time_tag.normalized_utc.isoformat() == "2026-09-18T00:00:01+00:00"
    assert envelope.payload.payload_type == "STATE_VECTOR"
    assert envelope.payload.reference_frame == "GCRF"
    assert envelope.payload.covariance_6x6 is None
    assert envelope.payload.covariance_source_ref is None


def test_opm_canonicalization_accepts_covariance_only_with_explicit_provenance_reference():
    parsed = parse_opm_v3_kvn_profile(OPM)
    envelope = opm_profile_to_canonical_envelope(
        parsed,
        observation_id="CCSDS-OPM-OBS-002",
        source_event_id="CCSDS-OPM-EVENT-002",
        source_sequence=2,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(OPM),
        received_at=RECEIVED,
        covariance_6x6=covariance(),
        covariance_reference_frame="GCRF",
        covariance_source_ref="fixture:qualified-covariance-001",
    )

    assert envelope.payload.covariance_6x6 is not None
    assert envelope.payload.covariance_source_ref == "fixture:qualified-covariance-001"

    with pytest.raises(ValidationError, match="cannot exist without covariance"):
        SdaCanonicalStateVector(
            reference_frame="GCRF",
            position_km=(1.0, 2.0, 3.0),
            velocity_km_s=(0.1, 0.2, 0.3),
            covariance_6x6=None,
            covariance_reference_frame=None,
            covariance_source_ref="invented",
        )



def test_opm_embedded_covariance_flows_to_canonical_with_reference_frame_and_provenance():
    parsed = parse_opm_v3_kvn_profile(OPM_WITH_COVARIANCE)
    envelope = opm_profile_to_canonical_envelope(
        parsed,
        observation_id="CCSDS-OPM-COV-001",
        source_event_id="CCSDS-OPM-COV-EVENT-001",
        source_sequence=5,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(OPM_WITH_COVARIANCE),
        received_at=RECEIVED,
    )

    assert envelope.payload.covariance_6x6 is not None
    assert envelope.payload.covariance_reference_frame == "RTN"
    assert (
        envelope.payload.covariance_source_ref
        == "CCSDS_OPM:POSITION_VELOCITY_COVARIANCE"
    )
    assert envelope.payload.covariance_6x6[0][0] == pytest.approx(4.0)
    assert envelope.payload.covariance_6x6[5][5] == pytest.approx(0.06)


def test_external_covariance_cannot_override_embedded_opm_covariance():
    parsed = parse_opm_v3_kvn_profile(OPM_WITH_COVARIANCE)
    with pytest.raises(ValueError, match="cannot override"):
        opm_profile_to_canonical_envelope(
            parsed,
            observation_id="CCSDS-OPM-COV-002",
            source_event_id="CCSDS-OPM-COV-EVENT-002",
            source_sequence=6,
            source=source(),
            contract=contract(),
            raw_source_digest=source_text_sha256(OPM_WITH_COVARIANCE),
            received_at=RECEIVED,
            covariance_6x6=covariance(),
            covariance_reference_frame="GCRF",
            covariance_source_ref="external:should-not-win",
        )


def test_external_covariance_requires_frame_and_provenance():
    parsed = parse_opm_v3_kvn_profile(OPM)
    with pytest.raises(ValueError, match="requires explicit reference frame and provenance"):
        opm_profile_to_canonical_envelope(
            parsed,
            observation_id="CCSDS-OPM-COV-003",
            source_event_id="CCSDS-OPM-COV-EVENT-003",
            source_sequence=7,
            source=source(),
            contract=contract(),
            raw_source_digest=source_text_sha256(OPM),
            received_at=RECEIVED,
            covariance_6x6=covariance(),
        )


def test_non_utc_or_noncalendar_time_is_preserved_raw_not_silently_normalized():
    non_utc = OPM.replace("TIME_SYSTEM = UTC", "TIME_SYSTEM = TAI").replace(
        "EPOCH = 2026-09-18T00:00:01",
        "EPOCH = 2026-261T00:00:01",
    )
    parsed = parse_opm_v3_kvn_profile(non_utc)
    envelope = opm_profile_to_canonical_envelope(
        parsed,
        observation_id="CCSDS-OPM-OBS-003",
        source_event_id="CCSDS-OPM-EVENT-003",
        source_sequence=3,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(non_utc),
        received_at=RECEIVED,
    )

    assert envelope.time_tag.raw == "2026-261T00:00:01"
    assert envelope.time_tag.time_system == "TAI"
    assert envelope.time_tag.normalized_utc is None


def test_tdm_range_canonicalization_preserves_measurement_semantics_without_fabricating_target_identity():
    parsed = parse_tdm_v2_range_kvn_profile(TDM)
    envelopes = tdm_range_profile_to_canonical_envelopes(
        parsed,
        observation_id_prefix="CCSDS-TDM-OBS",
        source_event_id_prefix="CCSDS-TDM-EVENT",
        first_source_sequence=40,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(TDM),
        received_at=RECEIVED,
    )

    assert len(envelopes) == 2
    assert [item.source_sequence for item in envelopes] == [40, 41]
    assert [item.payload.value for item in envelopes] == pytest.approx([1234.5, 1234.75])
    for envelope in envelopes:
        assert envelope.object_identity is None
        assert envelope.payload.payload_type == "RANGE"
        assert envelope.payload.units == "km"
        assert envelope.payload.participant_1 == "WS-SYNTH-STATION"
        assert envelope.payload.participant_2 == "WS-SYNTH-OBJECT"
        assert envelope.payload.path == "1,2,1"
        assert envelope.time_tag.normalized_utc is not None


def test_state_vector_envelope_cannot_drop_object_identity():
    with pytest.raises(ValidationError, match="requires object identity"):
        SdaCanonicalEnvelope(
            observation_id="CANONICAL-INVALID-001",
            source_event_id="CANONICAL-INVALID-EVENT-001",
            source_sequence=1,
            source=source(),
            object_identity=None,
            time_tag=SdaCanonicalTimeTag(
                raw="2026-09-18T00:00:01",
                time_system="UTC",
                normalized_utc=datetime(2026, 9, 18, 0, 0, 1, tzinfo=timezone.utc),
            ),
            received_at=RECEIVED,
            payload=SdaCanonicalStateVector(
                reference_frame="GCRF",
                position_km=(1.0, 2.0, 3.0),
                velocity_km_s=(0.1, 0.2, 0.3),
            ),
            raw_source_digest="sha256:" + "a" * 64,
            interface_contract_id=contract().contract_id,
            interface_contract_digest=contract().digest(),
            source_standard="CCSDS 502.0-B-3",
            source_profile="WS-CCSDS-OPM-V3-KVN-SUBSET-V1",
        )


def test_object_and_center_identity_are_semantic_not_decorative():
    parsed = parse_opm_v3_kvn_profile(OPM)
    first = opm_profile_to_canonical_envelope(
        parsed,
        observation_id="CCSDS-OPM-OBS-004",
        source_event_id="CCSDS-OPM-EVENT-004",
        source_sequence=4,
        source=source(),
        contract=contract(),
        raw_source_digest=source_text_sha256(OPM),
        received_at=RECEIVED,
    )
    changed = first.model_copy(
        update={
            "object_identity": SdaObjectIdentity(
                object_id="DIFFERENT-OBJECT",
                object_name=first.object_identity.object_name if first.object_identity else None,
                center_name="MARS",
            )
        }
    )

    assert first.semantic_digest() != changed.semantic_digest()

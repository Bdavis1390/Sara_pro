from __future__ import annotations

from datetime import timezone

import pytest

from worldshepherd_sara.sda_ccsds import (
    CCSDS_ODM_SPEC,
    CCSDS_TDM_SPEC,
    CcsdsKvnProfileError,
    parse_opm_v3_kvn_profile,
    parse_tdm_v2_range_kvn_profile,
    parse_utc_calendar_time,
    render_opm_v3_kvn_profile,
    render_tdm_v2_range_kvn_profile,
)


OPM_V3 = """CCSDS_OPM_VERS = 3.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
MESSAGE_ID = WS-SYNTH-OPM-001
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


OPM_V3_COVARIANCE = OPM_V3 + """COV_REF_FRAME = RTN
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


TDM_V2_RANGE = """CCSDS_TDM_VERS = 2.0
CREATION_DATE = 2026-09-18T00:00:00
ORIGINATOR = WORLDSHEPHERD
MESSAGE_ID = WS-SYNTH-TDM-001
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


def test_opm_v3_authoritative_version_profile_extracts_cartesian_state():
    message = parse_opm_v3_kvn_profile(OPM_V3)

    assert message.standard == CCSDS_ODM_SPEC
    assert message.version == "3.0"
    assert message.object_id == "2026-999A"
    assert message.reference_frame == "GCRF"
    assert message.time_system == "UTC"
    assert message.position_km == pytest.approx((7000.0, -1200.5, 350.25))
    assert message.velocity_km_s == pytest.approx((0.1, 7.4, -0.3))
    assert message.extra_keywords == {}


def test_opm_v3_round_trip_preserves_worldshepherd_profile_semantics():
    first = parse_opm_v3_kvn_profile(OPM_V3)
    rendered = render_opm_v3_kvn_profile(first)
    second = parse_opm_v3_kvn_profile(rendered)

    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    assert second.digest() == first.digest()


def test_opm_profile_preserves_unmodeled_optional_keywords_without_claiming_full_validation():
    text = OPM_V3 + "MASS = 500.0 [kg]\nUSER_DEFINED_NOTE = bounded-profile\n"
    message = parse_opm_v3_kvn_profile(text)

    assert message.extra_keywords["MASS"] == ["500.0 [kg]"]
    assert message.extra_keywords["USER_DEFINED_NOTE"] == ["bounded-profile"]


@pytest.mark.parametrize(
    ("replacement", "match"),
    [
        ("CCSDS_OPM_VERS = 2.0", "only CCSDS_OPM_VERS = 3.0"),
        ("X = 7000.0 [m]", r"X must explicitly declare \[km\]"),
        ("X_DOT = 100.0 [m/s]", r"X_DOT must explicitly declare \[km/s\]"),
    ],
)
def test_opm_profile_rejects_legacy_version_and_unit_ambiguity(replacement, match):
    if replacement.startswith("CCSDS"):
        text = OPM_V3.replace("CCSDS_OPM_VERS = 3.0", replacement)
    elif replacement.startswith("X ="):
        text = OPM_V3.replace("X = 7000.0 [km]", replacement)
    else:
        text = OPM_V3.replace("X_DOT = 0.1 [km/s]", replacement)

    with pytest.raises(CcsdsKvnProfileError, match=match):
        parse_opm_v3_kvn_profile(text)


def test_opm_profile_rejects_duplicate_required_keyword_and_nonfinite_text():
    duplicate = OPM_V3 + "X = 7000.0 [km]\n"
    with pytest.raises(CcsdsKvnProfileError, match="X must occur exactly once"):
        parse_opm_v3_kvn_profile(duplicate)

    nonfinite = OPM_V3.replace("X = 7000.0 [km]", "X = NaN [km]")
    with pytest.raises(CcsdsKvnProfileError, match="X is not a valid finite"):
        parse_opm_v3_kvn_profile(nonfinite)



def test_opm_profile_parses_complete_authoritative_lower_triangular_covariance():
    message = parse_opm_v3_kvn_profile(OPM_V3_COVARIANCE)

    assert message.covariance_reference_frame == "RTN"
    assert message.covariance_6x6 is not None
    assert message.covariance_6x6[0][0] == pytest.approx(4.0)
    assert message.covariance_6x6[1][1] == pytest.approx(9.0)
    assert message.covariance_6x6[2][2] == pytest.approx(16.0)
    assert message.covariance_6x6[3][3] == pytest.approx(0.04)
    assert message.covariance_6x6[4][4] == pytest.approx(0.05)
    assert message.covariance_6x6[5][5] == pytest.approx(0.06)
    assert message.covariance_6x6[0][1] == message.covariance_6x6[1][0] == 0.0

    rendered = render_opm_v3_kvn_profile(message)
    reparsed = parse_opm_v3_kvn_profile(rendered)
    assert reparsed.model_dump(mode="json") == message.model_dump(mode="json")


def test_opm_covariance_defaults_to_state_reference_frame_when_cov_ref_frame_omitted():
    text = OPM_V3_COVARIANCE.replace("COV_REF_FRAME = RTN\n", "")
    message = parse_opm_v3_kvn_profile(text)
    assert message.covariance_reference_frame == "GCRF"


def test_opm_covariance_is_all_or_none_and_unit_checked():
    partial = OPM_V3 + "CX_X = 4.0 [km**2]\n"
    with pytest.raises(CcsdsKvnProfileError, match="all-or-none"):
        parse_opm_v3_kvn_profile(partial)

    orphan_frame = OPM_V3 + "COV_REF_FRAME = RTN\n"
    with pytest.raises(CcsdsKvnProfileError, match="cannot appear without"):
        parse_opm_v3_kvn_profile(orphan_frame)

    wrong_unit = OPM_V3_COVARIANCE.replace(
        "CX_DOT_X_DOT = 0.04 [km**2/s**2]",
        "CX_DOT_X_DOT = 0.04 [m**2/s**2]",
    )
    with pytest.raises(CcsdsKvnProfileError, match=r"CX_DOT_X_DOT must explicitly declare \[km\*\*2/s\*\*2\]"):
        parse_opm_v3_kvn_profile(wrong_unit)


def test_tdm_v2_range_profile_extracts_explicit_unit_and_observations():
    message = parse_tdm_v2_range_kvn_profile(TDM_V2_RANGE)

    assert message.standard == CCSDS_TDM_SPEC
    assert message.version == "2.0"
    assert message.time_system == "UTC"
    assert message.participant_1 == "WS-SYNTH-STATION"
    assert message.participant_2 == "WS-SYNTH-OBJECT"
    assert message.path == "1,2,1"
    assert message.range_units == "km"
    assert [item.value for item in message.observations] == pytest.approx(
        [1234.5, 1234.75]
    )


def test_tdm_v2_range_round_trip_preserves_worldshepherd_profile_semantics():
    first = parse_tdm_v2_range_kvn_profile(TDM_V2_RANGE)
    rendered = render_tdm_v2_range_kvn_profile(first)
    second = parse_tdm_v2_range_kvn_profile(rendered)

    assert second.model_dump(mode="json") == first.model_dump(mode="json")
    assert second.digest() == first.digest()


@pytest.mark.parametrize(
    ("old", "new", "match"),
    [
        ("CCSDS_TDM_VERS = 2.0", "CCSDS_TDM_VERS = 1.0", "only CCSDS_TDM_VERS = 2.0"),
        ("RANGE_UNITS = km", "RANGE_UNITS = m", "must be one of km, s, or RU"),
        ("RANGE = 2026-09-18T00:00:01 1234.5", "ANGLE_1 = 2026-09-18T00:00:01 1.0", "unsupported TDM data keyword"),
    ],
)
def test_tdm_profile_rejects_wrong_version_units_and_unsupported_observable(old, new, match):
    with pytest.raises(CcsdsKvnProfileError, match=match):
        parse_tdm_v2_range_kvn_profile(TDM_V2_RANGE.replace(old, new))


def test_tdm_profile_rejects_marker_reordering_and_duplicate_required_metadata():
    reordered = TDM_V2_RANGE.replace(
        "META_STOP\nDATA_START",
        "DATA_START\nMETA_STOP",
    )
    with pytest.raises(CcsdsKvnProfileError, match="META_START < META_STOP"):
        parse_tdm_v2_range_kvn_profile(reordered)

    duplicate = TDM_V2_RANGE.replace(
        "RANGE_UNITS = km",
        "RANGE_UNITS = km\nRANGE_UNITS = km",
    )
    with pytest.raises(CcsdsKvnProfileError, match="RANGE_UNITS must occur exactly once"):
        parse_tdm_v2_range_kvn_profile(duplicate)


def test_bounded_utc_parser_does_not_silently_accept_ccsds_ordinal_time():
    parsed = parse_utc_calendar_time("2026-09-18T00:00:01")
    assert parsed.tzinfo == timezone.utc
    assert parsed.isoformat() == "2026-09-18T00:00:01+00:00"

    with pytest.raises(CcsdsKvnProfileError, match="calendar-form"):
        parse_utc_calendar_time("2026-261T00:00:01")

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .qualification import canonical_digest


CCSDS_ODM_SPEC = "CCSDS 502.0-B-3"
CCSDS_ODM_SPEC_URL = "https://ccsds.org/Pubs/502x0b3e1.pdf"
CCSDS_TDM_SPEC = "CCSDS 503.0-B-2"
CCSDS_TDM_SPEC_URL = "https://ccsds.org/Pubs/503x0b2c1.pdf"

WS_OPM_PROFILE = "WS-CCSDS-OPM-V3-KVN-SUBSET-V1"
WS_TDM_RANGE_PROFILE = "WS-CCSDS-TDM-V2-KVN-RANGE-SUBSET-V1"


class CcsdsKvnProfileError(ValueError):
    pass


_ASSIGNMENT = re.compile(r"^([A-Z0-9_]+)\s*=\s*(.*?)\s*$")
_NUMBER_WITH_OPTIONAL_UNIT = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
    r"(?:\s*\[([^\]]+)\])?$"
)


def _clean_lines(text: str) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise CcsdsKvnProfileError("CCSDS KVN input must be non-empty text")
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("COMMENT"):
            continue
        lines.append(line)
    return lines


def _assignments(lines: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for line in lines:
        match = _ASSIGNMENT.fullmatch(line)
        if match is None:
            continue
        result.setdefault(match.group(1), []).append(match.group(2).strip())
    return result


def _exact_one(mapping: dict[str, list[str]], key: str) -> str:
    values = mapping.get(key, [])
    if len(values) != 1:
        raise CcsdsKvnProfileError(
            f"{key} must occur exactly once in this Worldshepherd CCSDS profile"
        )
    return values[0]


def _parse_finite_number(value: str, *, key: str, expected_unit: str | None = None) -> float:
    match = _NUMBER_WITH_OPTIONAL_UNIT.fullmatch(value)
    if match is None:
        raise CcsdsKvnProfileError(f"{key} is not a valid finite numeric field")
    number = float(match.group(1))
    if not math.isfinite(number):
        raise CcsdsKvnProfileError(f"{key} must be finite")
    unit = match.group(2)
    if expected_unit is not None and unit != expected_unit:
        raise CcsdsKvnProfileError(
            f"{key} must explicitly declare [{expected_unit}] in this profile"
        )
    return number


class CcsdsOpmV3StateVector(BaseModel):
    """Bounded extraction profile for the mandatory Cartesian OPM state-vector path.

    This model is intentionally narrower than CCSDS 502.0-B-3. Successful parsing
    establishes compliance with the Worldshepherd subset only, not full ODM
    conformance.
    """

    model_config = ConfigDict(extra="forbid")

    profile: Literal[WS_OPM_PROFILE] = WS_OPM_PROFILE
    standard: Literal[CCSDS_ODM_SPEC] = CCSDS_ODM_SPEC
    version: Literal["3.0"] = "3.0"
    creation_date: str = Field(min_length=1)
    originator: str = Field(min_length=1)
    message_id: str | None = None
    object_name: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    center_name: str = Field(min_length=1)
    reference_frame: str = Field(min_length=1)
    time_system: str = Field(min_length=1)
    epoch: str = Field(min_length=1)
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    extra_keywords: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("position_km", "velocity_km_s")
    @classmethod
    def vectors_are_finite(cls, value: tuple[float, float, float]):
        if not all(math.isfinite(item) for item in value):
            raise ValueError("CCSDS state-vector values must be finite")
        return value

    def digest(self) -> str:
        return canonical_digest(self)


_OPM_REQUIRED = {
    "CCSDS_OPM_VERS",
    "CREATION_DATE",
    "ORIGINATOR",
    "OBJECT_NAME",
    "OBJECT_ID",
    "CENTER_NAME",
    "REF_FRAME",
    "TIME_SYSTEM",
    "EPOCH",
    "X",
    "Y",
    "Z",
    "X_DOT",
    "Y_DOT",
    "Z_DOT",
}


def parse_opm_v3_kvn_profile(text: str) -> CcsdsOpmV3StateVector:
    lines = _clean_lines(text)
    mapping = _assignments(lines)

    version = _exact_one(mapping, "CCSDS_OPM_VERS")
    if version != "3.0":
        raise CcsdsKvnProfileError(
            "Worldshepherd OPM profile accepts only CCSDS_OPM_VERS = 3.0"
        )

    required = {key: _exact_one(mapping, key) for key in sorted(_OPM_REQUIRED)}
    message_values = mapping.get("MESSAGE_ID", [])
    if len(message_values) > 1:
        raise CcsdsKvnProfileError("MESSAGE_ID may occur at most once in this profile")

    position = (
        _parse_finite_number(required["X"], key="X", expected_unit="km"),
        _parse_finite_number(required["Y"], key="Y", expected_unit="km"),
        _parse_finite_number(required["Z"], key="Z", expected_unit="km"),
    )
    velocity = (
        _parse_finite_number(required["X_DOT"], key="X_DOT", expected_unit="km/s"),
        _parse_finite_number(required["Y_DOT"], key="Y_DOT", expected_unit="km/s"),
        _parse_finite_number(required["Z_DOT"], key="Z_DOT", expected_unit="km/s"),
    )

    extras = {
        key: list(values)
        for key, values in mapping.items()
        if key not in _OPM_REQUIRED and key != "MESSAGE_ID"
    }
    return CcsdsOpmV3StateVector(
        creation_date=required["CREATION_DATE"],
        originator=required["ORIGINATOR"],
        message_id=message_values[0] if message_values else None,
        object_name=required["OBJECT_NAME"],
        object_id=required["OBJECT_ID"],
        center_name=required["CENTER_NAME"],
        reference_frame=required["REF_FRAME"],
        time_system=required["TIME_SYSTEM"],
        epoch=required["EPOCH"],
        position_km=position,
        velocity_km_s=velocity,
        extra_keywords=extras,
    )


def render_opm_v3_kvn_profile(message: CcsdsOpmV3StateVector) -> str:
    lines = [
        "CCSDS_OPM_VERS = 3.0",
        f"CREATION_DATE = {message.creation_date}",
        f"ORIGINATOR = {message.originator}",
    ]
    if message.message_id is not None:
        lines.append(f"MESSAGE_ID = {message.message_id}")
    lines.extend(
        [
            f"OBJECT_NAME = {message.object_name}",
            f"OBJECT_ID = {message.object_id}",
            f"CENTER_NAME = {message.center_name}",
            f"REF_FRAME = {message.reference_frame}",
            f"TIME_SYSTEM = {message.time_system}",
            f"EPOCH = {message.epoch}",
            f"X = {message.position_km[0]:.17g} [km]",
            f"Y = {message.position_km[1]:.17g} [km]",
            f"Z = {message.position_km[2]:.17g} [km]",
            f"X_DOT = {message.velocity_km_s[0]:.17g} [km/s]",
            f"Y_DOT = {message.velocity_km_s[1]:.17g} [km/s]",
            f"Z_DOT = {message.velocity_km_s[2]:.17g} [km/s]",
        ]
    )
    return "\n".join(lines) + "\n"


class CcsdsTdmRangeObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    epoch: str = Field(min_length=1)
    value: float

    @field_validator("value")
    @classmethod
    def value_is_finite(cls, value: float):
        if not math.isfinite(value):
            raise ValueError("TDM RANGE value must be finite")
        return value


class CcsdsTdmV2RangeSegment(BaseModel):
    """Worldshepherd single-segment RANGE extraction profile for TDM 2.0 KVN."""

    model_config = ConfigDict(extra="forbid")

    profile: Literal[WS_TDM_RANGE_PROFILE] = WS_TDM_RANGE_PROFILE
    standard: Literal[CCSDS_TDM_SPEC] = CCSDS_TDM_SPEC
    version: Literal["2.0"] = "2.0"
    creation_date: str = Field(min_length=1)
    originator: str = Field(min_length=1)
    message_id: str | None = None
    time_system: str = Field(min_length=1)
    participant_1: str = Field(min_length=1)
    participant_2: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    path: str = Field(min_length=1)
    range_units: Literal["km", "s", "RU"]
    observations: list[CcsdsTdmRangeObservation] = Field(min_length=1)
    extra_metadata: dict[str, list[str]] = Field(default_factory=dict)

    def digest(self) -> str:
        return canonical_digest(self)


_TDM_META_REQUIRED = {
    "TIME_SYSTEM",
    "PARTICIPANT_1",
    "PARTICIPANT_2",
    "MODE",
    "PATH",
    "RANGE_UNITS",
}


def _marker_index(lines: list[str], marker: str) -> int:
    positions = [index for index, line in enumerate(lines) if line == marker]
    if len(positions) != 1:
        raise CcsdsKvnProfileError(
            f"{marker} must occur exactly once in the single-segment Worldshepherd TDM profile"
        )
    return positions[0]


def parse_tdm_v2_range_kvn_profile(text: str) -> CcsdsTdmV2RangeSegment:
    lines = _clean_lines(text)

    meta_start = _marker_index(lines, "META_START")
    meta_stop = _marker_index(lines, "META_STOP")
    data_start = _marker_index(lines, "DATA_START")
    data_stop = _marker_index(lines, "DATA_STOP")
    if not (meta_start < meta_stop < data_start < data_stop):
        raise CcsdsKvnProfileError(
            "TDM profile requires META_START < META_STOP < DATA_START < DATA_STOP"
        )

    header_map = _assignments(lines[:meta_start])
    metadata_map = _assignments(lines[meta_start + 1 : meta_stop])

    version = _exact_one(header_map, "CCSDS_TDM_VERS")
    if version != "2.0":
        raise CcsdsKvnProfileError(
            "Worldshepherd TDM profile accepts only CCSDS_TDM_VERS = 2.0"
        )

    creation_date = _exact_one(header_map, "CREATION_DATE")
    originator = _exact_one(header_map, "ORIGINATOR")
    message_values = header_map.get("MESSAGE_ID", [])
    if len(message_values) > 1:
        raise CcsdsKvnProfileError("MESSAGE_ID may occur at most once in this profile")

    required = {
        key: _exact_one(metadata_map, key)
        for key in sorted(_TDM_META_REQUIRED)
    }
    if required["RANGE_UNITS"] not in {"km", "s", "RU"}:
        raise CcsdsKvnProfileError(
            "RANGE_UNITS must be one of km, s, or RU in CCSDS TDM"
        )

    observations: list[CcsdsTdmRangeObservation] = []
    for line in lines[data_start + 1 : data_stop]:
        match = _ASSIGNMENT.fullmatch(line)
        if match is None:
            raise CcsdsKvnProfileError(
                "TDM data lines must be KVN assignments in this profile"
            )
        key, raw_value = match.group(1), match.group(2).strip()
        if key != "RANGE":
            raise CcsdsKvnProfileError(
                f"unsupported TDM data keyword in RANGE subset: {key}"
            )
        parts = raw_value.split()
        if len(parts) != 2:
            raise CcsdsKvnProfileError(
                "RANGE data must contain exactly a time tag and one numeric value"
            )
        observations.append(
            CcsdsTdmRangeObservation(
                epoch=parts[0],
                value=_parse_finite_number(parts[1], key="RANGE"),
            )
        )

    if not observations:
        raise CcsdsKvnProfileError("TDM RANGE subset requires at least one RANGE observation")

    extras = {
        key: list(values)
        for key, values in metadata_map.items()
        if key not in _TDM_META_REQUIRED
    }
    return CcsdsTdmV2RangeSegment(
        creation_date=creation_date,
        originator=originator,
        message_id=message_values[0] if message_values else None,
        time_system=required["TIME_SYSTEM"],
        participant_1=required["PARTICIPANT_1"],
        participant_2=required["PARTICIPANT_2"],
        mode=required["MODE"],
        path=required["PATH"],
        range_units=required["RANGE_UNITS"],
        observations=observations,
        extra_metadata=extras,
    )


def render_tdm_v2_range_kvn_profile(message: CcsdsTdmV2RangeSegment) -> str:
    lines = [
        "CCSDS_TDM_VERS = 2.0",
        f"CREATION_DATE = {message.creation_date}",
        f"ORIGINATOR = {message.originator}",
    ]
    if message.message_id is not None:
        lines.append(f"MESSAGE_ID = {message.message_id}")
    lines.extend(
        [
            "META_START",
            f"TIME_SYSTEM = {message.time_system}",
            f"PARTICIPANT_1 = {message.participant_1}",
            f"PARTICIPANT_2 = {message.participant_2}",
            f"MODE = {message.mode}",
            f"PATH = {message.path}",
            f"RANGE_UNITS = {message.range_units}",
            "META_STOP",
            "DATA_START",
        ]
    )
    for observation in message.observations:
        lines.append(f"RANGE = {observation.epoch} {observation.value:.17g}")
    lines.append("DATA_STOP")
    return "\n".join(lines) + "\n"


def parse_utc_calendar_time(value: str) -> datetime:
    """Parse only explicit calendar-form UTC used by the bounded profile.

    CCSDS supports additional time representations/time systems. Those are
    intentionally rejected here until a dedicated time-scale adapter is qualified.
    """

    if "T" not in value or len(value.split("T", 1)[0].split("-")) != 3:
        raise CcsdsKvnProfileError(
            "bounded UTC adapter accepts only calendar-form YYYY-MM-DDThh:mm:ss timestamps"
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CcsdsKvnProfileError("invalid calendar-form UTC timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed

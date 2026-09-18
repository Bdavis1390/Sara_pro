from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .qualification import canonical_digest
from .sda import SdaInterfaceContract, SdaSourceIdentity
from .sda_ccsds import (
    CCSDS_ODM_SPEC,
    CCSDS_TDM_SPEC,
    CcsdsOpmV3StateVector,
    CcsdsTdmV2RangeSegment,
    parse_utc_calendar_time,
)


SDA_CANONICAL_ENVELOPE_SCHEMA = "WS-SDA-CANONICAL-ENVELOPE-V2"
STATE_VECTOR_PAYLOAD = "STATE_VECTOR"
RANGE_PAYLOAD = "RANGE"


class SdaCanonicalTimeTag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str = Field(min_length=1, max_length=128)
    time_system: str = Field(min_length=1, max_length=32)
    normalized_utc: datetime | None = None

    @field_validator("normalized_utc")
    @classmethod
    def normalized_time_is_timezone_aware(cls, value: datetime | None):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("normalized_utc must be timezone-aware")
        return value.astimezone(timezone.utc)


class SdaObjectIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_id: str = Field(min_length=1, max_length=256)
    object_name: str | None = Field(default=None, max_length=256)
    center_name: str | None = Field(default=None, max_length=128)


def _validate_covariance(value: list[list[float]]) -> list[list[float]]:
    if len(value) != 6 or any(len(row) != 6 for row in value):
        raise ValueError("state-vector covariance must be exactly 6x6")
    if any(not math.isfinite(item) for row in value for item in row):
        raise ValueError("state-vector covariance values must be finite")
    for index in range(6):
        if value[index][index] < 0:
            raise ValueError("state-vector covariance diagonal must be non-negative")
        for other in range(6):
            scale = max(1.0, abs(value[index][other]), abs(value[other][index]))
            if abs(value[index][other] - value[other][index]) > 1e-12 * scale:
                raise ValueError("state-vector covariance must be symmetric")
    return value


class SdaCanonicalStateVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_type: Literal[STATE_VECTOR_PAYLOAD] = STATE_VECTOR_PAYLOAD
    reference_frame: str = Field(min_length=1, max_length=128)
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    covariance_6x6: list[list[float]] | None = None
    covariance_reference_frame: str | None = Field(default=None, max_length=128)
    covariance_source_ref: str | None = Field(default=None, max_length=512)

    @field_validator("position_km", "velocity_km_s")
    @classmethod
    def vectors_are_finite(cls, value: tuple[float, float, float]):
        if not all(math.isfinite(item) for item in value):
            raise ValueError("state-vector components must be finite")
        return value

    @field_validator("covariance_6x6")
    @classmethod
    def covariance_is_valid(cls, value: list[list[float]] | None):
        if value is None:
            return None
        return _validate_covariance(value)

    @model_validator(mode="after")
    def covariance_reference_is_consistent(self):
        if self.covariance_6x6 is None:
            if self.covariance_source_ref is not None:
                raise ValueError("covariance_source_ref cannot exist without covariance")
            if self.covariance_reference_frame is not None:
                raise ValueError("covariance_reference_frame cannot exist without covariance")
        else:
            if not self.covariance_reference_frame:
                raise ValueError("covariance requires covariance_reference_frame")
            if not self.covariance_source_ref:
                raise ValueError("covariance requires covariance_source_ref")
        return self


class SdaCanonicalRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_type: Literal[RANGE_PAYLOAD] = RANGE_PAYLOAD
    value: float
    units: Literal["km", "s", "RU"]
    participant_1: str = Field(min_length=1, max_length=256)
    participant_2: str = Field(min_length=1, max_length=256)
    mode: str = Field(min_length=1, max_length=128)
    path: str = Field(min_length=1, max_length=128)

    @field_validator("value")
    @classmethod
    def value_is_finite(cls, value: float):
        if not math.isfinite(value):
            raise ValueError("range value must be finite")
        return value


SdaCanonicalPayload = Annotated[
    Union[SdaCanonicalStateVector, SdaCanonicalRange],
    Field(discriminator="payload_type"),
]


class SdaCanonicalEnvelope(BaseModel):
    """Evidence-preserving canonical envelope for heterogeneous SDA measurements.

    V2 does not replace the V1 state-vector record yet. It prevents CCSDS data from
    being coerced into V1 when object identity, center identity, time semantics, or
    covariance provenance would otherwise be lost.
    """

    model_config = ConfigDict(extra="forbid")

    schema: Literal[SDA_CANONICAL_ENVELOPE_SCHEMA] = SDA_CANONICAL_ENVELOPE_SCHEMA
    observation_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,160}$")
    source_event_id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,160}$")
    source_sequence: int = Field(ge=0)
    source: SdaSourceIdentity
    object_identity: SdaObjectIdentity | None = None
    time_tag: SdaCanonicalTimeTag
    received_at: datetime
    payload: SdaCanonicalPayload

    raw_source_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    interface_contract_id: str = Field(min_length=1, max_length=128)
    interface_contract_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_standard: str = Field(min_length=1, max_length=128)
    source_profile: str = Field(min_length=1, max_length=128)
    source_message_id: str | None = Field(default=None, max_length=256)
    transformation_refs: list[str] = Field(default_factory=list, max_length=128)

    @field_validator("received_at")
    @classmethod
    def received_at_is_timezone_aware(cls, value: datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at must be timezone-aware")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def state_vector_requires_object_identity(self):
        if isinstance(self.payload, SdaCanonicalStateVector) and self.object_identity is None:
            raise ValueError("state-vector canonical evidence requires object identity")
        return self

    def semantic_digest(self) -> str:
        return canonical_digest(self)


def source_text_sha256(text: str) -> str:
    if not isinstance(text, str) or not text:
        raise ValueError("source text must be non-empty")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_time_tag(raw: str, time_system: str) -> SdaCanonicalTimeTag:
    normalized: datetime | None = None
    if time_system.upper() == "UTC":
        try:
            normalized = parse_utc_calendar_time(raw)
        except ValueError:
            normalized = None
    return SdaCanonicalTimeTag(
        raw=raw,
        time_system=time_system,
        normalized_utc=normalized,
    )


def opm_profile_to_canonical_envelope(
    message: CcsdsOpmV3StateVector,
    *,
    observation_id: str,
    source_event_id: str,
    source_sequence: int,
    source: SdaSourceIdentity,
    contract: SdaInterfaceContract,
    raw_source_digest: str,
    received_at: datetime,
    covariance_6x6: list[list[float]] | None = None,
    covariance_reference_frame: str | None = None,
    covariance_source_ref: str | None = None,
) -> SdaCanonicalEnvelope:
    if message.standard != CCSDS_ODM_SPEC:
        raise ValueError("OPM canonical adapter received the wrong source standard")
    if message.version != "3.0":
        raise ValueError("OPM canonical adapter requires version 3.0 profile")

    if message.covariance_6x6 is not None:
        if covariance_6x6 is not None:
            raise ValueError(
                "external covariance cannot override covariance already carried by OPM"
            )
        selected_covariance = message.covariance_6x6
        selected_covariance_frame = message.covariance_reference_frame
        selected_covariance_source = "CCSDS_OPM:POSITION_VELOCITY_COVARIANCE"
    elif covariance_6x6 is not None:
        if not covariance_reference_frame or not covariance_source_ref:
            raise ValueError(
                "external covariance requires explicit reference frame and provenance"
            )
        selected_covariance = covariance_6x6
        selected_covariance_frame = covariance_reference_frame
        selected_covariance_source = covariance_source_ref
    else:
        if covariance_reference_frame is not None or covariance_source_ref is not None:
            raise ValueError(
                "covariance reference/provenance cannot be supplied without covariance"
            )
        selected_covariance = None
        selected_covariance_frame = None
        selected_covariance_source = None

    return SdaCanonicalEnvelope(
        observation_id=observation_id,
        source_event_id=source_event_id,
        source_sequence=source_sequence,
        source=source,
        object_identity=SdaObjectIdentity(
            object_id=message.object_id,
            object_name=message.object_name,
            center_name=message.center_name,
        ),
        time_tag=_canonical_time_tag(message.epoch, message.time_system),
        received_at=received_at,
        payload=SdaCanonicalStateVector(
            reference_frame=message.reference_frame,
            position_km=message.position_km,
            velocity_km_s=message.velocity_km_s,
            covariance_6x6=selected_covariance,
            covariance_reference_frame=selected_covariance_frame,
            covariance_source_ref=selected_covariance_source,
        ),
        raw_source_digest=raw_source_digest,
        interface_contract_id=contract.contract_id,
        interface_contract_digest=contract.digest(),
        source_standard=message.standard,
        source_profile=message.profile,
        source_message_id=message.message_id,
        transformation_refs=[
            "parse:WS-CCSDS-OPM-V3-KVN-SUBSET-V1",
            "canonicalize:WS-SDA-CANONICAL-ENVELOPE-V2",
        ],
    )


def tdm_range_profile_to_canonical_envelopes(
    message: CcsdsTdmV2RangeSegment,
    *,
    observation_id_prefix: str,
    source_event_id_prefix: str,
    first_source_sequence: int,
    source: SdaSourceIdentity,
    contract: SdaInterfaceContract,
    raw_source_digest: str,
    received_at: datetime,
) -> tuple[SdaCanonicalEnvelope, ...]:
    if message.standard != CCSDS_TDM_SPEC:
        raise ValueError("TDM canonical adapter received the wrong source standard")
    if message.version != "2.0":
        raise ValueError("TDM canonical adapter requires version 2.0 profile")

    results: list[SdaCanonicalEnvelope] = []
    for index, observation in enumerate(message.observations):
        sequence = first_source_sequence + index
        results.append(
            SdaCanonicalEnvelope(
                observation_id=f"{observation_id_prefix}-{index + 1:04d}",
                source_event_id=f"{source_event_id_prefix}-{index + 1:04d}",
                source_sequence=sequence,
                source=source,
                object_identity=None,
                time_tag=_canonical_time_tag(observation.epoch, message.time_system),
                received_at=received_at,
                payload=SdaCanonicalRange(
                    value=observation.value,
                    units=message.range_units,
                    participant_1=message.participant_1,
                    participant_2=message.participant_2,
                    mode=message.mode,
                    path=message.path,
                ),
                raw_source_digest=raw_source_digest,
                interface_contract_id=contract.contract_id,
                interface_contract_digest=contract.digest(),
                source_standard=message.standard,
                source_profile=message.profile,
                source_message_id=message.message_id,
                transformation_refs=[
                    "parse:WS-CCSDS-TDM-V2-KVN-RANGE-SUBSET-V1",
                    "canonicalize:WS-SDA-CANONICAL-ENVELOPE-V2",
                ],
            )
        )
    return tuple(results)

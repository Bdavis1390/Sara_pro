from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


PBA_SCHEMA_VERSION = "ws-pba-0.3"


class PBAState(StrEnum):
    SAFE_OFF = "SAFE_OFF"
    DISCOVERY = "DISCOVERY"
    ATTESTED = "ATTESTED"
    STATE_VALIDATION = "STATE_VALIDATION"
    AUTHORIZATION_PENDING = "AUTHORIZATION_PENDING"
    VERIFY_ONLY = "VERIFY_ONLY"
    DELIVERY_AUTHORIZED = "DELIVERY_AUTHORIZED"
    RAMP_DOWN = "RAMP_DOWN"
    SAFE_HOLD = "SAFE_HOLD"
    FAULT_LATCHED = "FAULT_LATCHED"


class OperatingState(StrEnum):
    VERIFY_ONLY = "VERIFY_ONLY"
    DELIVERY_AUTHORIZED = "DELIVERY_AUTHORIZED"


class SafeToBeamAuthorization(BaseModel):
    """Bounded PRIME authorization object for a partner-controlled energy system.

    This object grants permission to enter a bounded operating state. It does not
    contain beam-control, pointing, targeting, or hardware-drive instructions.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["ws-pba-0.3"] = PBA_SCHEMA_VERSION
    authorization_id: UUID
    mission_id: str = Field(min_length=1, max_length=128)

    transmitter_id: str = Field(min_length=1, max_length=256)
    receiver_id: str = Field(min_length=1, max_length=256)

    transmitter_attestation: str = Field(min_length=1, max_length=512)
    receiver_attestation: str = Field(min_length=1, max_length=512)
    configuration_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    navigation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tracking_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    valid_from: datetime
    valid_until: datetime
    allowed_state: OperatingState

    policy_id: str = Field(min_length=1, max_length=128)
    authority_id: str = Field(min_length=1, max_length=128)

    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    nonce: str = Field(min_length=16, max_length=256)
    sequence: int = Field(ge=0)
    signature: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def validate_window(self) -> "SafeToBeamAuthorization":
        if self.valid_from.tzinfo is None or self.valid_until.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        return self


class PBAObservation(BaseModel):
    """Normalized partner-neutral assurance inputs.

    The fields are deliberately semantic rather than hardware-specific so the
    Worldshepherd assurance layer can remain independent of beam technology.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    transmitter_id: str = Field(min_length=1, max_length=256)
    receiver_id: str = Field(min_length=1, max_length=256)
    configuration_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    navigation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tracking_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    transmitter_attested: bool
    receiver_attested: bool
    navigation_valid: bool
    tracking_valid: bool
    telemetry_fresh: bool
    safety_veto: bool = False
    critical_state_disagreement: bool = False
    configuration_changed: bool = False
    identity_changed: bool = False

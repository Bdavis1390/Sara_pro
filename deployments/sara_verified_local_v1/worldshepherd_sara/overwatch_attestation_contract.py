from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .overwatch_tripwire import OverwatchObservation


OVERWATCH_ATTESTATION_CONTRACT_SCHEMA = "WS-OVERWATCH-ATTESTATION-CONTRACT-V1"
MAX_OVERWATCH_ATTESTATION_CONTRACT_LIFETIME = timedelta(seconds=30)


class OverwatchAttestationContract(BaseModel):
    """Interface contract for a future authenticated OVERWATCH observation.

    Phase 8B establishes only the data boundary. An instance of this model does
    not authenticate the monitor, authorize execution, alter FASA readiness, or
    prove that any containment side effect occurred.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema: Literal["WS-OVERWATCH-ATTESTATION-CONTRACT-V1"] = (
        OVERWATCH_ATTESTATION_CONTRACT_SCHEMA
    )
    attestation_id: str = Field(min_length=1, max_length=160)
    observation: OverwatchObservation
    issued_at: datetime
    expires_at: datetime
    nonce: str = Field(min_length=16, max_length=128)
    verification_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    authorization_effect: Literal["NONE"] = "NONE"
    execution_effect_applied: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract_window(self) -> "OverwatchAttestationContract":
        if self.issued_at.tzinfo is None or self.issued_at.utcoffset() is None:
            raise ValueError("issued_at must be timezone-aware")
        if self.expires_at.tzinfo is None or self.expires_at.utcoffset() is None:
            raise ValueError("expires_at must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")
        if (
            self.expires_at - self.issued_at
            > MAX_OVERWATCH_ATTESTATION_CONTRACT_LIFETIME
        ):
            raise ValueError("attestation contract lifetime exceeds 30 seconds")
        return self

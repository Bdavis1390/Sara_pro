from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

from .apnt_adapter import NormalizedPntSource
from .qualification import canonical_digest


class AuthoritativeInterfaceContract(BaseModel):
    contract_id: str = Field(min_length=1)
    interface_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    authoritative_spec_ref: str = Field(min_length=1)
    authoritative_spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    field_mapping: dict[str, str] = Field(default_factory=dict)
    validated_fields: list[str] = Field(default_factory=list)
    partner_validation_ref: str | None = None
    enabled: bool = False

    @model_validator(mode="after")
    def enabling_requires_minimum_mapping(self) -> "AuthoritativeInterfaceContract":
        required = {"source_id", "source_kind", "health", "confidence"}
        if self.enabled:
            if not required.issubset(self.field_mapping):
                raise ValueError("enabled APNT interface contract lacks required normalized field mapping")
            if not required.issubset(set(self.validated_fields)):
                raise ValueError("enabled APNT interface contract lacks validation evidence for required fields")
        return self

    def digest(self) -> str:
        return canonical_digest(self)


class ContractPntAdapter:
    """Map an external payload only through an explicit authoritative contract.

    The adapter refuses to run until the contract has authoritative spec identity,
    required field mappings, and explicit validation markers. This does not itself
    prove ASPN/pntOS/GPNTS interoperability or partner/platform acceptance.
    """

    def __init__(self, contract: AuthoritativeInterfaceContract) -> None:
        if not contract.enabled:
            raise ValueError("interface contract is not enabled")
        self.contract = contract
        self.adapter_name = f"contract:{contract.contract_id}"

    def normalize(self, payload: dict[str, Any]) -> NormalizedPntSource:
        mapping = self.contract.field_mapping
        missing = [external for external in mapping.values() if external not in payload]
        if missing:
            raise ValueError(f"external payload missing contracted fields: {sorted(missing)}")
        return NormalizedPntSource(
            source_id=str(payload[mapping["source_id"]]),
            source_kind=str(payload[mapping["source_kind"]]),
            health=str(payload[mapping["health"]]),
            confidence=float(payload[mapping["confidence"]]),
            observed_utc=(
                str(payload[mapping["observed_utc"]])
                if mapping.get("observed_utc") and mapping["observed_utc"] in payload
                else None
            ),
            attributes={
                "contract_id": self.contract.contract_id,
                "contract_digest": self.contract.digest(),
                "authoritative_spec_ref": self.contract.authoritative_spec_ref,
            },
        )
